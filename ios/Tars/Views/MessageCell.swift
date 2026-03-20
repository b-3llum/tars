import UIKit

final class MessageCell: UITableViewCell {

    static let reuseID = "MessageCell"

    private let bubbleView = UIView()
    private let messageLabel = UILabel()
    private let timestampLabel = UILabel()
    private let confirmStack = UIStackView()
    private let confirmButton = UIButton(type: .system)
    private let denyButton = UIButton(type: .system)

    var onConfirm: (() -> Void)?
    var onDeny: (() -> Void)?

    // Constraints toggled per sender
    private var leadingConstraint: NSLayoutConstraint!
    private var trailingConstraint: NSLayoutConstraint!

    override init(style: UITableViewCell.CellStyle, reuseIdentifier: String?) {
        super.init(style: style, reuseIdentifier: reuseIdentifier)
        selectionStyle = .none
        backgroundColor = .clear
        contentView.backgroundColor = .clear
        setupViews()
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) not implemented") }

    // MARK: - Setup

    private func setupViews() {
        bubbleView.layer.cornerRadius = 14
        bubbleView.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(bubbleView)

        messageLabel.numberOfLines = 0
        messageLabel.font = .systemFont(ofSize: 15)
        messageLabel.translatesAutoresizingMaskIntoConstraints = false
        bubbleView.addSubview(messageLabel)

        timestampLabel.font = .systemFont(ofSize: 10)
        timestampLabel.textColor = .secondaryLabel
        timestampLabel.translatesAutoresizingMaskIntoConstraints = false
        bubbleView.addSubview(timestampLabel)

        confirmButton.setTitle("Confirm", for: .normal)
        confirmButton.addTarget(self, action: #selector(didTapConfirm), for: .touchUpInside)
        denyButton.setTitle("Deny", for: .normal)
        denyButton.setTitleColor(.systemRed, for: .normal)
        denyButton.addTarget(self, action: #selector(didTapDeny), for: .touchUpInside)

        confirmStack.axis = .horizontal
        confirmStack.spacing = 16
        confirmStack.addArrangedSubview(confirmButton)
        confirmStack.addArrangedSubview(denyButton)
        confirmStack.translatesAutoresizingMaskIntoConstraints = false
        bubbleView.addSubview(confirmStack)

        leadingConstraint = bubbleView.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 12)
        trailingConstraint = bubbleView.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -12)

        NSLayoutConstraint.activate([
            bubbleView.topAnchor.constraint(equalTo: contentView.topAnchor, constant: 4),
            bubbleView.bottomAnchor.constraint(equalTo: contentView.bottomAnchor, constant: -4),
            bubbleView.widthAnchor.constraint(lessThanOrEqualTo: contentView.widthAnchor, multiplier: 0.78),

            messageLabel.topAnchor.constraint(equalTo: bubbleView.topAnchor, constant: 10),
            messageLabel.leadingAnchor.constraint(equalTo: bubbleView.leadingAnchor, constant: 14),
            messageLabel.trailingAnchor.constraint(equalTo: bubbleView.trailingAnchor, constant: -14),

            timestampLabel.topAnchor.constraint(equalTo: messageLabel.bottomAnchor, constant: 4),
            timestampLabel.trailingAnchor.constraint(equalTo: bubbleView.trailingAnchor, constant: -14),

            confirmStack.topAnchor.constraint(equalTo: timestampLabel.bottomAnchor, constant: 6),
            confirmStack.leadingAnchor.constraint(equalTo: bubbleView.leadingAnchor, constant: 14),
            confirmStack.bottomAnchor.constraint(equalTo: bubbleView.bottomAnchor, constant: -10),
        ])
    }

    // MARK: - Configure

    func configure(with message: ChatMessage) {
        messageLabel.text = message.text

        let formatter = DateFormatter()
        formatter.timeStyle = .short
        timestampLabel.text = formatter.string(from: message.timestamp)

        let isUser = message.sender == .user
        bubbleView.backgroundColor = isUser
            ? UIColor.systemBlue
            : UIColor.secondarySystemBackground
        messageLabel.textColor = isUser ? .white : .label

        // Layout: user bubbles right-aligned, TARS left-aligned
        leadingConstraint.isActive = !isUser
        trailingConstraint.isActive = isUser

        // Confirmation buttons
        confirmStack.isHidden = !message.requiresConfirmation
    }

    // MARK: - Actions

    @objc private func didTapConfirm() { onConfirm?() }
    @objc private func didTapDeny() { onDeny?() }
}
