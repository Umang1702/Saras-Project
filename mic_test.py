import speech_recognition as sr

DEVICE_INDEX = 20

print("Available microphones:")
for i, name in enumerate(sr.Microphone.list_microphone_names()):
    print(f"{i}: {name}")

print()
print(f"Testing microphone device {DEVICE_INDEX}...")
print(f"Device name: {sr.Microphone.list_microphone_names()[DEVICE_INDEX]}")

recognizer = sr.Recognizer()

microphone = None

try:
    microphone = sr.Microphone(device_index=DEVICE_INDEX)

    print()
    print("Opening microphone...")

    with microphone as source:
        print("Microphone opened successfully.")
        print("Calibrating for background noise...")

        recognizer.adjust_for_ambient_noise(
            source,
            duration=1
        )

        print()
        print("================================")
        print("SPEAK NOW: Say 'Saras'")
        print("================================")

        audio = recognizer.listen(
            source,
            timeout=10,
            phrase_time_limit=10,
        )

    print()
    print("Audio captured successfully.")
    print("Sending audio for recognition...")

    text = recognizer.recognize_google(audio)

    print()
    print("==============================")
    print("SUCCESS")
    print("==============================")
    print("Recognized text:", repr(text))

except sr.WaitTimeoutError:
    print()
    print("ERROR: No speech detected within 10 seconds.")

except sr.UnknownValueError:
    print()
    print("ERROR: Microphone audio was captured,")
    print("but speech could not be understood.")

except sr.RequestError as exc:
    print()
    print("ERROR: Google Speech Recognition service failed:")
    print(exc)

except Exception as exc:
    print()
    print("==============================")
    print("MICROPHONE ERROR")
    print("==============================")
    print("Type:", type(exc).__name__)
    print("Message:", str(exc))