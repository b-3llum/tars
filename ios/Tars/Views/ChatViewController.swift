import UIKit

final class ChatViewController: UIViewController {

    // MARK: - UI Elements

    private let tableView = UITableView()
    private let inputField = UITextField()
    private let sendButton = UIButton(type: .system)
    private let micButton = UIButton(type: .system)
    private let speakerButton = UIButton(type: .system)
    private let inputBar = UIView()

    private var messages: [ChatMessage] = []
    private let network = NetworkManager.shared
    private let speech = SpeechManager.shared

    /// When true, TARS speaks responses aloud.
    private var voiceOutputEnabled = true

    // MARK: - Lifecycle

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "TARS"
        view.backgroundColor = UIColor(red: 0.05, green: 0.05, blue: 0.07, alpha: 1)
        setupNavBar()
        setupInputBar()
        setupTableView()
        setupKeyboardObservers()

        // Request speech permissions on first launch
        speech.requestPermissions { _ in }

        // Interstellar-style greeting
        let greeting = ChatMessage(
            text: "TARS online. Humor setting: 75%. How can I help you, Cooper?",
            sender: .tars
        )
        messages.append(greeting)
        speakIfEnabled(greeting.text)
    }

    // MARK: - Nav Bar

    private func setupNavBar() {
        let appearance = UINavigationBarAppearance()
        appearance.configureWithOpaqueBackground()
        appearance.backgroundColor = UIColor(red: 0.05, green: 0.05, blue: 0.07, alpha: 1)
        appearance.titleTextAttributes = [
            .foregroundColor: UIColor(red: 0, green: 0.9, blue: 0.9, alpha: 1),
            .font: UIFont.monospacedSystemFont(ofSize: 18, weight: .bold),
        ]
        navigationController?.navigationBar.standardAppearance = appearance
        navigationController?.navigationBar.scrollEdgeAppearance = appearance
    }

    // MARK: - Layout

    private func setupTableView() {
        tableView.dataSource = self
        tableView.delegate = self
        tableView.register(MessageCell.self, forCellReuseIdentifier: MessageCell.reuseID)
        tableView.separatorStyle = .none
        tableView.backgroundColor = .clear
        tableView.keyboardDismissMode = .interactive
        tableView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(tableView)

        NSLayoutConstraint.activate([
            tableView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            tableView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            tableView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            tableView.bottomAnchor.constraint(equalTo: inputBar.topAnchor),
        ])
    }

    private func setupInputBar() {
        inputBar.backgroundColor = UIColor(red: 0.08, green: 0.08, blue: 0.1, alpha: 1)
        inputBar.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(inputBar)

        inputField.placeholder = "Talk to TARS..."
        inputField.borderStyle = .roundedRect
        inputField.returnKeyType = .send
        inputField.delegate = self
        inputField.backgroundColor = UIColor(red: 0.12, green: 0.12, blue: 0.14, alpha: 1)
        inputField.textColor = .white
        inputField.attributedPlaceholder = NSAttributedString(
            string: "Talk to TARS...",
            attributes: [.foregroundColor: UIColor.gray]
        )
        inputField.translatesAutoresizingMaskIntoConstraints = false
        inputBar.addSubview(inputField)

        // Mic button (speech-to-text)
        micButton.setImage(UIImage(systemName: "mic.circle.fill"), for: .normal)
        micButton.tintColor = UIColor(red: 0, green: 0.9, blue: 0.9, alpha: 1)
        micButton.addTarget(self, action: #selector(didTapMic), for: .touchUpInside)
        micButton.translatesAutoresizingMaskIntoConstraints = false
        inputBar.addSubview(micButton)

        // Speaker toggle (text-to-speech on/off)
        updateSpeakerIcon()
        speakerButton.tintColor = UIColor(red: 0, green: 0.9, blue: 0.9, alpha: 1)
        speakerButton.addTarget(self, action: #selector(didTapSpeaker), for: .touchUpInside)
        speakerButton.translatesAutoresizingMaskIntoConstraints = false
        inputBar.addSubview(speakerButton)

        // Send button
        sendButton.setImage(UIImage(systemName: "arrow.up.circle.fill"), for: .normal)
        sendButton.tintColor = UIColor(red: 0, green: 0.9, blue: 0.9, alpha: 1)
        sendButton.addTarget(self, action: #selector(didTapSend), for: .touchUpInside)
        sendButton.translatesAutoresizingMaskIntoConstraints = false
        inputBar.addSubview(sendButton)

        NSLayoutConstraint.activate([
            inputBar.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            inputBar.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            inputBar.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor),
            inputBar.heightAnchor.constraint(equalToConstant: 56),

            speakerButton.leadingAnchor.constraint(equalTo: inputBar.leadingAnchor, constant: 8),
            speakerButton.centerYAnchor.constraint(equalTo: inputBar.centerYAnchor),
            speakerButton.widthAnchor.constraint(equalToConstant: 36),
            speakerButton.heightAnchor.constraint(equalToConstant: 36),

            inputField.leadingAnchor.constraint(equalTo: speakerButton.trailingAnchor, constant: 4),
            inputField.centerYAnchor.constraint(equalTo: inputBar.centerYAnchor),
            inputField.trailingAnchor.constraint(equalTo: micButton.leadingAnchor, constant: -4),
            inputField.heightAnchor.constraint(equalToConstant: 38),

            micButton.trailingAnchor.constraint(equalTo: sendButton.leadingAnchor, constant: -4),
            micButton.centerYAnchor.constraint(equalTo: inputBar.centerYAnchor),
            micButton.widthAnchor.constraint(equalToConstant: 36),
            micButton.heightAnchor.constraint(equalToConstant: 36),

            sendButton.trailingAnchor.constraint(equalTo: inputBar.trailingAnchor, constant: -8),
            sendButton.centerYAnchor.constraint(equalTo: inputBar.centerYAnchor),
            sendButton.widthAnchor.constraint(equalToConstant: 36),
            sendButton.heightAnchor.constraint(equalToConstant: 36),
        ])
    }

    // MARK: - Keyboard

    private func setupKeyboardObservers() {
        NotificationCenter.default.addObserver(
            self, selector: #selector(keyboardWillChange(_:)),
            name: UIResponder.keyboardWillChangeFrameNotification, object: nil
        )
    }

    @objc private func keyboardWillChange(_ note: Notification) {
        guard let frame = note.userInfo?[UIResponder.keyboardFrameEndUserInfoKey] as? CGRect,
              let duration = note.userInfo?[UIResponder.keyboardAnimationDurationUserInfoKey] as? Double else { return }

        let offset = view.frame.height - frame.origin.y
        UIView.animate(withDuration: duration) {
            self.additionalSafeAreaInsets.bottom = max(offset - self.view.safeAreaInsets.bottom, 0)
            self.view.layoutIfNeeded()
        }
    }

    // MARK: - Speech-to-Text (Mic)

    @objc private func didTapMic() {
        if speech.isListening {
            speech.stopListening()
            micButton.tintColor = UIColor(red: 0, green: 0.9, blue: 0.9, alpha: 1)
            micButton.setImage(UIImage(systemName: "mic.circle.fill"), for: .normal)
            return
        }

        // Visual feedback — red while recording
        micButton.tintColor = .systemRed
        micButton.setImage(UIImage(systemName: "mic.fill"), for: .normal)

        speech.startListening { [weak self] text, isFinal in
            DispatchQueue.main.async {
                self?.inputField.text = text
                if isFinal {
                    self?.micButton.tintColor = UIColor(red: 0, green: 0.9, blue: 0.9, alpha: 1)
                    self?.micButton.setImage(UIImage(systemName: "mic.circle.fill"), for: .normal)
                    // Auto-send when speech finishes
                    self?.didTapSend()
                }
            }
        } onError: { [weak self] error in
            DispatchQueue.main.async {
                self?.micButton.tintColor = UIColor(red: 0, green: 0.9, blue: 0.9, alpha: 1)
                self?.micButton.setImage(UIImage(systemName: "mic.circle.fill"), for: .normal)
                self?.appendMessage(ChatMessage(text: "Mic error: \(error)", sender: .tars))
            }
        }
    }

    // MARK: - Speaker Toggle

    @objc private func didTapSpeaker() {
        voiceOutputEnabled.toggle()
        updateSpeakerIcon()
        if !voiceOutputEnabled {
            speech.stopSpeaking()
        }
    }

    private func updateSpeakerIcon() {
        let icon = voiceOutputEnabled ? "speaker.wave.3.fill" : "speaker.slash.fill"
        speakerButton.setImage(UIImage(systemName: icon), for: .normal)
    }

    // MARK: - Send

    @objc private func didTapSend() {
        guard let text = inputField.text?.trimmingCharacters(in: .whitespacesAndNewlines),
              !text.isEmpty else { return }

        inputField.text = ""
        appendMessage(ChatMessage(text: text, sender: .user))

        network.sendRequest(message: text) { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success(let resp):
                    let msg = ChatMessage(
                        text: resp.response,
                        sender: .tars,
                        actionId: resp.actionId,
                        requiresConfirmation: resp.requiresConfirmation ?? false
                    )
                    self?.appendMessage(msg)
                    self?.speakIfEnabled(resp.response)

                case .failure(let error):
                    let errText = "Error: \(error.localizedDescription)"
                    self?.appendMessage(ChatMessage(text: errText, sender: .tars))
                    self?.speakIfEnabled("Something went wrong. Check the connection.")
                }
            }
        }
    }

    // MARK: - Confirm / Deny

    private func confirmAction(actionId: String) {
        network.confirm(actionId: actionId, confirmed: true) { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success(let resp):
                    self?.appendMessage(ChatMessage(text: resp.response, sender: .tars))
                    self?.speakIfEnabled(resp.response)
                case .failure(let error):
                    self?.appendMessage(ChatMessage(text: "Error: \(error.localizedDescription)", sender: .tars))
                }
            }
        }
    }

    private func denyAction(actionId: String) {
        network.confirm(actionId: actionId, confirmed: false) { [weak self] _ in
            DispatchQueue.main.async {
                self?.appendMessage(ChatMessage(text: "Action cancelled.", sender: .tars))
                self?.speakIfEnabled("Understood. Standing down.")
            }
        }
    }

    // MARK: - Helpers

    private func appendMessage(_ message: ChatMessage) {
        messages.append(message)
        let indexPath = IndexPath(row: messages.count - 1, section: 0)
        tableView.insertRows(at: [indexPath], with: .automatic)
        tableView.scrollToRow(at: indexPath, at: .bottom, animated: true)
    }

    private func speakIfEnabled(_ text: String) {
        guard voiceOutputEnabled else { return }
        speech.speak(text)
    }
}

// MARK: - UITableViewDataSource & Delegate

extension ChatViewController: UITableViewDataSource, UITableViewDelegate {

    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        messages.count
    }

    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: MessageCell.reuseID, for: indexPath) as! MessageCell
        let msg = messages[indexPath.row]
        cell.configure(with: msg)

        if let actionId = msg.actionId {
            cell.onConfirm = { [weak self] in self?.confirmAction(actionId: actionId) }
            cell.onDeny    = { [weak self] in self?.denyAction(actionId: actionId) }
        }

        return cell
    }

    func tableView(_ tableView: UITableView, estimatedHeightForRowAt indexPath: IndexPath) -> CGFloat {
        60
    }

    func tableView(_ tableView: UITableView, heightForRowAt indexPath: IndexPath) -> CGFloat {
        UITableView.automaticDimension
    }
}

// MARK: - UITextFieldDelegate

extension ChatViewController: UITextFieldDelegate {
    func textFieldShouldReturn(_ textField: UITextField) -> Bool {
        didTapSend()
        return true
    }
}
