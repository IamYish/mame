// license:BSD-3-Clause
// L6028 Playback Lab: firmware-free deterministic device fixture.
// NO original MPC2000 operating system, CPU, simulated DAC or new sound path.
#include "emu.h"
#include "sound/l7a1045_l6028_dsp_a.h"
#include "speaker.h"

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
	required_device<l7a1045_sound_device> m_dsp;
	emu_timer *m_test_timer = nullptr;

	void pcm_map(address_map &map) ATTR_COLD;
	void load_samples();
	void start_voice(u8 voice, u32 first_sample);
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

void l6028lab_state::start_voice(u8 voice, u32 first_sample)
{
	// 48-bit L6028 registers, written as three little-endian 16-bit words.
	// Existing device handlers perform ALL interpretation and playback.
	u64 const reg[8] = {
		u64(first_sample) << 12,                                      // start, RAM
		(u64(first_sample + SAMPLE_LENGTH) << 12) | 0x1000,           // end, 4.12 pitch=1
		(u64(0xf000) << 16) | SAMPLE_LENGTH,                           // loop length
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
		load_samples();
		logerror("L6028_LAB_BEGIN sample_rate=%u words=%u\n", SAMPLE_RATE, SAMPLE_LENGTH);
		start_voice(0, SAMPLE_A);
		m_test_timer->adjust(attotime::from_ticks(220, SAMPLE_RATE), 1);
		break;
	case 1:
		logerror("L6028_LAB_OVERLAP voice=1\n");
		start_voice(1, SAMPLE_B);
		m_test_timer->adjust(attotime::from_ticks(2048, SAMPLE_RATE), 2);
		break;
	case 2:
		// Force the device's stream updater through the final fixture boundary.
		m_dsp->lab_host_w(0x00, 0x0000);
		logerror("L6028_LAB_DONE voices=2\n");
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
