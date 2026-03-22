import Foundation
import AVFoundation
import Speech

@MainActor
final class ChatViewModel: ObservableObject {

    @Published var messages: [ChatMessage] = []
    @Published var isListening = false
    @Published var isThinking = false
    @Published var voiceOutputEnabled = true

    private let network = NetworkManager.shared
    private let synthesizer = AVSpeechSynthesizer()

    // Speech recognition
    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private let audioEngine = AVAudioEngine()
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?

    init() {
        messages.append(ChatMessage(
            text: "TARS online. Humor setting: 75%. How can I help you, Cooper?",
            sender: .tars
        ))
        speakIfEnabled("TARS online. Humor setting: 75%.")
        requestPermissions()
    }

    // MARK: - Send message

    func send(message: String) {
        let userMsg = ChatMessage(text: message, sender: .user)
        messages.append(userMsg)
        isThinking = true

        network.sendRequest(message: message) { [weak self] result in
            DispatchQueue.main.async {
                guard let self else { return }
                self.isThinking = false
                switch result {
                case .success(let resp):
                    let msg = ChatMessage(
                        text: resp.response,
                        sender: .tars,
                        actionId: resp.actionId,
                        requiresConfirmation: resp.requiresConfirmation ?? false
                    )
                    self.messages.append(msg)
                    self.speakIfEnabled(resp.response)

                case .failure(let error):
                    let msg = ChatMessage(
                        text: "Error: \(error.localizedDescription)",
                        sender: .tars
                    )
                    self.messages.append(msg)
                    self.speakIfEnabled("Something went wrong. Check the connection.")
                }
            }
        }
    }

    // MARK: - Confirm / Deny

    func confirm(actionId: String) {
        isThinking = true
        network.confirm(actionId: actionId, confirmed: true) { [weak self] result in
            DispatchQueue.main.async {
                guard let self else { return }
                self.isThinking = false
                switch result {
                case .success(let resp):
                    self.messages.append(ChatMessage(text: resp.response, sender: .tars))
                    self.speakIfEnabled(resp.response)
                case .failure(let error):
                    self.messages.append(ChatMessage(text: "Error: \(error.localizedDescription)", sender: .tars))
                }
            }
        }
    }

    func deny(actionId: String) {
        network.confirm(actionId: actionId, confirmed: false) { [weak self] _ in
            DispatchQueue.main.async {
                self?.messages.append(ChatMessage(text: "Action cancelled.", sender: .tars))
                self?.speakIfEnabled("Understood. Standing down.")
            }
        }
    }

    // MARK: - Text-to-Speech

    /// TARS voice — uses the premium "Aaron" voice (deep US male) if available,
    /// falls back to enhanced Daniel (British), then compact Daniel.
    /// To use a downloaded voice, go to:
    ///   Settings > Accessibility > Spoken Content > Voices > English
    ///   and download "Aaron (Enhanced)" or "Daniel (Enhanced)" for best quality.
    func speakIfEnabled(_ text: String) {
        guard voiceOutputEnabled else { return }

        // Switch audio session to playback so it goes through the speaker
        try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .default)
        try? AVAudioSession.sharedInstance().setActive(true)

        let utterance = AVSpeechUtterance(string: text)

        // Try voices in order of preference — deep, authoritative, robotic feel
        let preferredVoices = [
            "com.apple.voice.enhanced.en-US.Aaron",      // Deep US male (best)
            "com.apple.voice.compact.en-US.Aaron",        // Deep US male (compact)
            "com.apple.voice.enhanced.en-GB.Daniel",      // British male (enhanced)
            "com.apple.voice.compact.en-GB.Daniel",       // British male (compact)
        ]

        utterance.voice = preferredVoices
            .compactMap { AVSpeechSynthesisVoice(identifier: $0) }
            .first ?? AVSpeechSynthesisVoice(language: "en-US")

        utterance.rate = 0.50          // Deliberate, not rushed
        utterance.pitchMultiplier = 0.80   // Low pitch — robotic authority
        utterance.volume = 1.0
        utterance.preUtteranceDelay = 0.1  // Slight pause before speaking

        synthesizer.speak(utterance)
    }

    func stopSpeaking() {
        synthesizer.stopSpeaking(at: .immediate)
    }

    // MARK: - Speech-to-Text

    private func requestPermissions() {
        SFSpeechRecognizer.requestAuthorization { _ in }
        AVAudioSession.sharedInstance().requestRecordPermission { _ in }
    }

    func toggleListening(onPartial: @escaping (String) -> Void,
                         onFinished: @escaping (String) -> Void) {
        if isListening {
            stopListening()
            return
        }

        guard let recognizer = speechRecognizer, recognizer.isAvailable else { return }

        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.record, mode: .measurement, options: .duckOthers)
            try audioSession.setActive(true, options: .notifyOthersOnDeactivation)
        } catch { return }

        recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
        guard let request = recognitionRequest else { return }
        request.shouldReportPartialResults = true

        let inputNode = audioEngine.inputNode
        let format = inputNode.outputFormat(forBus: 0)

        inputNode.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
            request.append(buffer)
        }

        recognitionTask = recognizer.recognitionTask(with: request) { [weak self] result, error in
            guard let self else { return }
            if let result = result {
                let text = result.bestTranscription.formattedString
                DispatchQueue.main.async {
                    if result.isFinal {
                        self.stopListening()
                        onFinished(text)
                    } else {
                        onPartial(text)
                    }
                }
            }
            if error != nil {
                DispatchQueue.main.async { self.stopListening() }
            }
        }

        audioEngine.prepare()
        do {
            try audioEngine.start()
            DispatchQueue.main.async { self.isListening = true }
        } catch {
            stopListening()
        }
    }

    private func stopListening() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionRequest = nil
        recognitionTask?.cancel()
        recognitionTask = nil
        isListening = false
    }
}
