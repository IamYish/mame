// license:BSD-3-Clause
// L6028 Playback Lab: firmware-free deterministic device fixture.
// NO original MPC2000 operating system, CPU, simulated DAC or new sound path.
#include "emu.h"
#include "sound/l7a1045_l6028_dsp_a.h"
#include "speaker.h"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <fstream>
#include <string_view>

namespace {

class l6028lab_state : public driver_device
{
public:
	l6028lab_state(machine_config const &mconfig, device_type type, char const *tag)
		: driver_device(mconfig, type, tag), m_dsp(*this, "dsp") { }
	void l6028lab(machine_config &config);

protected:
	virtual void machine_start() override ATTR_COLD;
	virtual void machine_reset() override ATTR_COLD;

private:
	static constexpr u32 SAMPLE_A = 0x1000;
	static constexpr u32 SAMPLE_B = 0x3000;
	static constexpr u32 SAMPLE_LENGTH = 0x1000;
	static constexpr u32 SAMPLE_RATE = 44100;
	static constexpr u32 PACK_SLOT_WORDS = 0x8000;
	static constexpr u32 PACK_FIRST_WORD = 0x1000;
	static constexpr u32 PACK_STAGGER_FRAMES = 4410;
	struct pack_event { u32 frame; u8 voice; bool start; };
	std::array<pack_event, 16> m_pack_events{};
	std::array<u32, 8> m_pack_frames{};
	std::array<u32, 8> m_pack_padded{};
	u32 m_pack_next_event = 0;

	required_device<l7a1045_sound_device> m_dsp;
	emu_timer *m_test_timer = nullptr;

	void pcm_map(address_map &map) ATTR_COLD;
	void load_samples();
	bool load_private_pack();
	void stop_voice(u8 voice);
	void probe_atomic_envelope();
	void start_voice(u8 voice, u32 first_sample, u32 length);
	TIMER_CALLBACK_MEMBER(test_step);
	void dma_request(int state);
};

void l6028lab_state::pcm_map(address_map &map)
{
	map(0x0000'0000, 0x01ff'ffff).ram(); // same sample RAM as the MPC2000XL driver
}

void l6028lab_state::load_samples()
{
	address_space &ram = m_dsp->space(AS_DATA);
	for (u32 i = 0; i < SAMPLE_LENGTH; i++)
	{
		// Integer-only, known PCM stimulus: pulse/decay and signed saw.
		s32 const decay = (i < 768) ? s32((768 - i) * 24) : 0;
		s32 const a = (i == 0) ? 24'576 : ((i / 16) & 1) ? -decay : decay;
		s32 const b = (s32(i & 255) - 128) * 96;
		ram.write_word((SAMPLE_A + i) << 1, u16(s16(a)));
		ram.write_word((SAMPLE_B + i) << 1, u16(s16(b)));
	}
}

bool l6028lab_state::load_private_pack()
{
	char const *const filename = std::getenv("L6028_SAMPLE_PACK");
	if (!filename || !*filename)
		return false;
	std::ifstream input(filename, std::ios::binary);
	if (!input)
		fatalerror("L6028 sample pack not readable: %s", filename);
	std::array<char, 8> magic{};
	if (!input.read(magic.data(), magic.size()) ||
		std::string_view(magic.data(), magic.size()) != "L6028PK1")
		fatalerror("L6028 pack: bad header magic");

	auto get32 = [&input]() -> u32
	{
		std::array<unsigned char, 4> b{};
		if (!input.read(reinterpret_cast<char *>(b.data()), b.size()))
			fatalerror("L6028 pack: truncated header");
		return u32(b[0]) | (u32(b[1]) << 8) | (u32(b[2]) << 16) | (u32(b[3]) << 24);
	};
	if (get32() != 8 || get32() != 0)
		fatalerror("L6028 pack: requires 8 samples and zero flags");
	for (u32 v = 0; v < 8; ++v)
	{
		m_pack_frames[v] = get32();
		m_pack_padded[v] = get32();
		if (!m_pack_frames[v] || m_pack_frames[v] > PACK_SLOT_WORDS - 16 ||
			m_pack_padded[v] < m_pack_frames[v] + 16 ||
			m_pack_padded[v] > PACK_SLOT_WORDS ||
			(m_pack_padded[v] & 15))
			fatalerror("L6028 pack: invalid sample length for voice %u", v);
	}
	address_space &ram = m_dsp->space(AS_DATA);
	for (u32 v = 0; v < 8; ++v)
	{
		u32 const base = PACK_FIRST_WORD + v * PACK_SLOT_WORDS;
		for (u32 i = 0; i < m_pack_padded[v]; ++i)
		{
			std::array<unsigned char, 2> bytes{};
			if (!input.read(reinterpret_cast<char *>(bytes.data()), bytes.size()))
				fatalerror("L6028 pack: missing voice %u, frame %u", v, i);
			ram.write_word((base + i) << 1, u16(bytes[0]) | (u16(bytes[1]) << 8));
		}
	}
	if (input.peek() != std::char_traits<char>::eof())
		fatalerror("L6028 pack: trailing data");
	logerror("L6028_PACK_READY voices=8 rate=44100\n");
	return true;
}

void l6028lab_state::probe_atomic_envelope()
{
	// 0x2000 is arbitrary probe data, NOT a recovered firmware default.
	constexpr u16 probe_value = 0x2000;
	logerror("L6028_ATOMIC_PROBE_BEGIN voice=0 reg=3 value=%04x\n", probe_value);
	m_dsp->lab_host_w(0x00, 0x0300);
	m_dsp->lab_host_w(0x04, probe_value);
	u16 const before = m_dsp->lab_host_r(0x04);
	m_dsp->lab_host_w(0x0c, 0);
	u16 const after_atomic = m_dsp->lab_host_r(0x04);
	m_dsp->lab_host_w(0x04, 0);
	u16 const after_regular = m_dsp->lab_host_r(0x04);
	logerror("L6028_ATOMIC_PROBE_RESULT before=%04x after_atomic=%04x after_regular=%04x\n",
		before, after_atomic, after_regular);
	// Assert CURRENT MAME semantics only. Do not infer behavior of real silicon.
	if (before != probe_value || after_atomic != probe_value || after_regular != 0)
		fatalerror("L6028 model atomic envelope semantics changed: inspect source");
}

void l6028lab_state::stop_voice(u8 voice)
{
	m_dsp->lab_host_w(0x00, (3 << 8) | voice);
	m_dsp->lab_host_w(0x02, 0); // real voice-envelope key-off handler
}

void l6028lab_state::start_voice(u8 voice, u32 first_sample, u32 length)
{
	// 48-bit L6028 registers, written as three little-endian 16-bit words.
	// Existing device handlers perform ALL interpretation and playback.
	u64 const reg[8] = {
		u64(first_sample) << 12,                                      // start, RAM
		(u64(first_sample + length) << 12) | 0x1000,           // end, 4.12 pitch=1
		(u64(0xf000) << 16) | length,                           // loop length
		u64(0xffff) << 16,                                           // volume envelope
		u64(0xffff) << 16,                                           // target, no ramp
		u64(0x7fff) << 16,                                           // filter cutoff
		u64(0x7ff0) << 16,                                           // filter target, res=0
		0x0000ffffULL                                                // 8-bit L/R 255, no send
	};
	for (u16 r = 0; r < 8; r++)
	{
		m_dsp->lab_host_w(0x00, (r << 8) | voice);
		for (u16 word = 0; word < 3; word++)
			m_dsp->lab_host_w(0x02 + 2 * word, (reg[r] >> (16 * word)) & 0xffff);
	}
	m_dsp->lab_host_w(0x00, voice);
	m_dsp->lab_host_w(0x08, 0x0100); // key-on, with DMA disabled
}

TIMER_CALLBACK_MEMBER(l6028lab_state::test_step)
{
	switch (param)
	{
	case 0:
		if (std::getenv("L6028_ATOMIC_PROBE"))
		{
			probe_atomic_envelope();
			machine().schedule_exit();
			break;
		}
		if (load_private_pack())
		{
			for (u32 v = 0; v < 8; ++v)
			{
				u32 const start = v * PACK_STAGGER_FRAMES;
				m_pack_events[2 * v] = { start, u8(v), true };
				m_pack_events[2 * v + 1] = { start + m_pack_frames[v], u8(v), false };
			}
			std::sort(m_pack_events.begin(), m_pack_events.end(), [](pack_event const &a, pack_event const &b)
			{
				if (a.frame != b.frame)
					return a.frame < b.frame;
				return a.start < b.start;
			});
			m_pack_next_event = 0;
			m_test_timer->adjust(attotime::zero, 4);
			break;
		}
		load_samples();
		logerror("L6028_LAB_BEGIN sample_rate=%u words=%u\n", SAMPLE_RATE, SAMPLE_LENGTH);
		start_voice(0, SAMPLE_A, SAMPLE_LENGTH);
		m_test_timer->adjust(attotime::from_ticks(220, SAMPLE_RATE), 1);
		break;
	case 1:
		logerror("L6028_LAB_OVERLAP voice=1\n");
		start_voice(1, SAMPLE_B, SAMPLE_LENGTH);
		m_test_timer->adjust(attotime::from_ticks(2048, SAMPLE_RATE), 2);
		break;
	case 2:
		// Force the device's stream updater through the final fixture boundary.
		m_dsp->lab_host_w(0x00, 0x0000);
		logerror("L6028_LAB_DONE voices=2\n");
		if (std::getenv("L6028_NATIVE_FLUSH"))
		{
			// Keep the frozen short PCM reference unchanged unless requested.
			// Release voices only AFTER rendering their original 2269 frames.
			stop_voice(0);
			stop_voice(1);
			m_test_timer->adjust(attotime::from_ticks(4096, SAMPLE_RATE), 6);
		}
		else
		{
			machine().schedule_exit();
		}
		break;
	case 4:
	{
		u32 const now = m_pack_events[m_pack_next_event].frame;
		do
		{
			pack_event const ev = m_pack_events[m_pack_next_event++];
			logerror("L6028_PACK_EVENT frame=%u voice=%u type=%s\n", ev.frame, ev.voice, ev.start ? "on" : "off");
			if (ev.start)
				start_voice(ev.voice, PACK_FIRST_WORD + ev.voice * PACK_SLOT_WORDS, m_pack_padded[ev.voice]);
			else
				stop_voice(ev.voice);
		} while (m_pack_next_event < m_pack_events.size() && m_pack_events[m_pack_next_event].frame == now);
		if (m_pack_next_event < m_pack_events.size())
			m_test_timer->adjust(attotime::from_ticks(m_pack_events[m_pack_next_event].frame - now, SAMPLE_RATE), 4);
		else
			m_test_timer->adjust(attotime::from_ticks(2048, SAMPLE_RATE), 5);
		break;
	}
	case 5:
		m_dsp->lab_host_w(0x00, 0x0000);
		logerror("L6028_PACK_DONE voices=8\n");
		machine().schedule_exit();
		break;
	case 6:
		logerror("L6028_LAB_NATIVE_FLUSH_DONE\n");
		machine().schedule_exit();
		break;
	}
}

void l6028lab_state::dma_request(int state)
{
	if (state)
		logerror("L6028_LAB_UNEXPECTED_DMA_REQUEST\n");
}

void l6028lab_state::machine_start()
{
	m_test_timer = timer_alloc(FUNC(l6028lab_state::test_step), this);
}

void l6028lab_state::machine_reset()
{
	m_test_timer->adjust(attotime::from_ticks(1, SAMPLE_RATE), 0);
}

void l6028lab_state::l6028lab(machine_config &config)
{
	L7A1045(config, m_dsp, 33.8688_MHz_XTAL);
	m_dsp->set_addrmap(AS_DATA, &l6028lab_state::pcm_map);
	m_dsp->drq_handler_cb().set(FUNC(l6028lab_state::dma_request));
	SPEAKER(config, "speaker", 2).front();
	SPEAKER(config, "outputs", 8).unknown();
	m_dsp->add_route(l7a1045_sound_device::L6028_LEFT, "speaker", 1.0, 0);
	m_dsp->add_route(l7a1045_sound_device::L6028_RIGHT, "speaker", 1.0, 1);
	for (int i = 0; i < 8; i++)
		m_dsp->add_route(l7a1045_sound_device::L6028_OUT0 + i, "outputs", 1.0, i);
}

static INPUT_PORTS_START(l6028lab)
INPUT_PORTS_END

ROM_START(l6028lab)
	ROM_REGION(0x10, "user1", ROMREGION_ERASE00) // intentionally no Akai ROM
ROM_END

} // anonymous namespace

CONS(2026, l6028lab, 0, 0, l6028lab, l6028lab, l6028lab_state, empty_init,
	"StaticPoint Audio / MAME research", "L6028 PCM Playback Lab (diagnostic)",
	0)
