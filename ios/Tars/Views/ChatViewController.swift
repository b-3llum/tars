import UIKit

final class ChatViewController: UIViewController {

    // MARK: - UI Elements

    private let tableView = UITableView()
    private let inputField = UITextField()
    private let sendButton = UIButton(type: .system)
    private let inputBar = UIView()

    private var messages: [ChatMessage] = []
    private let network = NetworkManager.shared

    // MARK: - Lifecycle

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "TARS"
        view.backgroundColor = .systemBackground
        setupInputBar()
        setupTableView()
        setupKeyboardObservers()

        // Initial greeting
        messages.append(ChatMessage(
            text: "TARS online. How can I assist you?",
            sender: .tars
        ))
    }

    // MARK: - Layout

    private func setupTableView() {
        tableView.dataSource = self
        tableView.delegate = self
        tableView.register(MessageCell.self, forCellReuseIdentifier: MessageCell.reuseID)
        tableView.separatorStyle = .none
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
        inputBar.backgroundColor = .secondarySystemBackground
        inputBar.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(inputBar)

        inputField.placeholder = "Message TARS..."
        inputField.borderStyle = .roundedRect
        inputField.returnKeyType = .send
        inputField.delegate = self
        inputField.translatesAutoresizingMaskIntoConstraints = false
        inputBar.addSubview(inputField)

        sendButton.setImage(UIImage(systemName: "arrow.up.circle.fill"), for: .normal)
        sendButton.tintColor = .systemBlue
        sendButton.addTarget(self, action: #selector(didTapSend), for: .touchUpInside)
        sendButton.translatesAutoresizingMaskIntoConstraints = false
        inputBar.addSubview(sendButton)

        NSLayoutConstraint.activate([
            inputBar.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            inputBar.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            inputBar.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor),
            inputBar.heightAnchor.constraint(equalToConstant: 56),

            inputField.leadingAnchor.constraint(equalTo: inputBar.leadingAnchor, constant: 12),
            inputField.centerYAnchor.constraint(equalTo: inputBar.centerYAnchor),
            inputField.trailingAnchor.constraint(equalTo: sendButton.leadingAnchor, constant: -8),
            inputField.heightAnchor.constraint(equalToConstant: 38),

            sendButton.trailingAnchor.constraint(equalTo: inputBar.trailingAnchor, constant: -12),
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
                    var msg = ChatMessage(
                        text: resp.response,
                        sender: .tars,
                        actionId: resp.actionId,
                        requiresConfirmation: resp.requiresConfirmation ?? false
                    )
                    self?.appendMessage(msg)

                case .failure(let error):
                    self?.appendMessage(ChatMessage(
                        text: "Error: \(error.localizedDescription)",
                        sender: .tars
                    ))
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
