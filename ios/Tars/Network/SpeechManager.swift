import AVFoundation
import Speech

/// Handles speech-to-text (microphone input) and text-to-speech (TARS voice output).
final class SpeechManager: NSObject {

    static let shared = SpeechManager()

    // MARK: - Text-to-Speech

    private let synthesizer = AVSpeechSynthesizer()

    /// Speak text aloud in a deep, robotic TARS-like voice.
    func speak(_ text: String, completion: (() -> Void)? = nil) {
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(identifier: "com.apple.voice.compact.en-GB.Daniel")
            ?? AVSpeechSynthesisVoice(language: "en-GB")
        utterance.rate = 0.48       // Slightly slow, deliberate
        utterance.pitchMultiplier = 0.85  // Lower pitch for robotic feel
        utterance.volume = 1.0

        speechCompletionHandler = completion
        synthesizer.delegate = self
        synthesizer.speak(utterance)
    }

    func stopSpeaking() {
        synthesizer.stopSpeaking(at: .immediate)
    }

    var isSpeaking: Bool { synthesizer.isSpeaking }

    private var speechCompletionHandler: (() -> Void)?

    // MARK: - Speech-to-Text

    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private let audioEngine = AVAudioEngine()
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?

    var isListening: Bool { audioEngine.isRunning }

    /// Request microphone + speech recognition permissions.
    func requestPermissions(completion: @escaping (Bool) -> Void) {
        SFSpeechRecognizer.requestAuthorization { speechStatus in
            guard speechStatus == .authorized else {
                completion(false)
                return
            }
            AVAudioSession.sharedInstance().requestRecordPermission { micGranted in
                DispatchQueue.main.async {
                    completion(micGranted)
                }
            }
        }
    }

    /// Start listening. Calls `onResult` with partial/final transcription text.
    /// Calls `onError` if something fails.
    func startListening(onResult: @escaping (String, Bool) -> Void,
                        onError: @escaping (String) -> Void) {
        // Stop any existing session
        stopListening()

        guard let recognizer = speechRecognizer, recognizer.isAvailable else {
            onError("Speech recognition is not available on this device.")
            return
        }

        let audioSession = AVAudioSession.sharedInstance()
        do {
            try audioSession.setCategory(.record, mode: .measurement, options: .duckOthers)
            try audioSession.setActive(true, options: .notifyOthersOnDeactivation)
        } catch {
            onError("Audio session error: \(error.localizedDescription)")
            return
        }

        recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
        guard let request = recognitionRequest else {
            onError("Could not create recognition request.")
            return
        }
        request.shouldReportPartialResults = true

        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)

        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { buffer, _ in
            request.append(buffer)
        }

        recognitionTask = recognizer.recognitionTask(with: request) { result, error in
            if let result = result {
                let text = result.bestTranscription.formattedString
                let isFinal = result.isFinal
                onResult(text, isFinal)

                if isFinal {
                    self.stopListening()
                }
            }

            if let error = error {
                self.stopListening()
                onError(error.localizedDescription)
            }
        }

        audioEngine.prepare()
        do {
            try audioEngine.start()
        } catch {
            onError("Audio engine failed to start: \(error.localizedDescription)")
        }
    }

    /// Stop the microphone and recognition.
    func stopListening() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionRequest = nil
        recognitionTask?.cancel()
        recognitionTask = nil
    }
}

// MARK: - AVSpeechSynthesizerDelegate

extension SpeechManager: AVSpeechSynthesizerDelegate {
    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer,
                           didFinish utterance: AVSpeechUtterance) {
        DispatchQueue.main.async {
            self.speechCompletionHandler?()
            self.speechCompletionHandler = nil
        }
    }
}
