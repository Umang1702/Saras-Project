import pyaudio

DEVICE_INDEX = 6

audio = pyaudio.PyAudio()

try:
    info = audio.get_device_info_by_index(DEVICE_INDEX)

    print("Testing:")
    print("Index:", DEVICE_INDEX)
    print("Device:", info["name"])
    print("Input channels:", info["maxInputChannels"])
    print("Sample rate:", info["defaultSampleRate"])
    print()

    print("Opening microphone...")

    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=44100,
        input=True,
        input_device_index=DEVICE_INDEX,
        frames_per_buffer=1024,
    )

    print("Microphone opened successfully.")
    print()
    print("==============================")
    print("SPEAK NOW: Say SARAS")
    print("==============================")

    for i in range(100):
        data = stream.read(
            1024,
            exception_on_overflow=False
        )

        if i % 10 == 0:
            print(f"Captured audio: {i}/100")

    print()
    print("SUCCESS: Audio capture is working.")

    stream.stop_stream()
    stream.close()

except Exception as exc:
    print()
    print("==============================")
    print("PYAUDIO ERROR")
    print("==============================")
    print("Type:", type(exc).__name__)
    print("Message:", str(exc))

finally:
    audio.terminate()