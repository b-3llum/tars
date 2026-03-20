import SwiftUI

struct ChatView: View {

    @StateObject private var viewModel = ChatViewModel()
    @State private var inputText = ""

    // Cyan accent matching the TARS monolith indicator
    private let tarsAccent = Color(red: 0, green: 0.9, blue: 0.9)

    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Messages list
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 8) {
                            ForEach(viewModel.messages) { msg in
                                MessageBubble(message: msg,
                                              onConfirm: { viewModel.confirm(actionId: $0) },
                                              onDeny: { viewModel.deny(actionId: $0) })
                                    .id(msg.id)
                            }
                        }
                        .padding(.horizontal, 12)
                        .padding(.top, 8)
                    }
                    .onChange(of: viewModel.messages.count) { _ in
                        if let last = viewModel.messages.last {
                            withAnimation {
                                proxy.scrollTo(last.id, anchor: .bottom)
                            }
                        }
                    }
                }

                Divider().background(Color.gray.opacity(0.3))

                // Input bar
                HStack(spacing: 8) {
                    // Speaker toggle
                    Button {
                        viewModel.voiceOutputEnabled.toggle()
                        if !viewModel.voiceOutputEnabled {
                            viewModel.stopSpeaking()
                        }
                    } label: {
                        Image(systemName: viewModel.voiceOutputEnabled
                              ? "speaker.wave.3.fill" : "speaker.slash.fill")
                            .font(.title3)
                            .foregroundColor(tarsAccent)
                    }

                    // Text field
                    TextField("Talk to TARS...", text: $inputText)
                        .textFieldStyle(.roundedBorder)
                        .submitLabel(.send)
                        .onSubmit { send() }

                    // Mic button
                    Button {
                        viewModel.toggleListening { transcript in
                            inputText = transcript
                        } onFinished: { finalText in
                            inputText = finalText
                            send()
                        }
                    } label: {
                        Image(systemName: viewModel.isListening ? "mic.fill" : "mic.circle.fill")
                            .font(.title2)
                            .foregroundColor(viewModel.isListening ? .red : tarsAccent)
                    }

                    // Send button
                    Button { send() } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.title2)
                            .foregroundColor(tarsAccent)
                    }
                    .disabled(inputText.trimmingCharacters(in: .whitespaces).isEmpty)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 8)
                .background(Color(UIColor.systemGray6).opacity(0.15))
            }
            .background(Color(red: 0.05, green: 0.05, blue: 0.07))
            .navigationTitle("TARS")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbarBackground(Color(red: 0.05, green: 0.05, blue: 0.07), for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
        }
    }

    private func send() {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        inputText = ""
        viewModel.send(message: text)
    }
}

// MARK: - Message Bubble

struct MessageBubble: View {
    let message: ChatMessage
    var onConfirm: ((String) -> Void)?
    var onDeny: ((String) -> Void)?

    private let tarsAccent = Color(red: 0, green: 0.9, blue: 0.9)

    var body: some View {
        HStack {
            if message.sender == .user { Spacer(minLength: 60) }

            VStack(alignment: message.sender == .user ? .trailing : .leading, spacing: 4) {
                Text(message.text)
                    .font(.system(size: 15))
                    .foregroundColor(message.sender == .user ? .white : .primary)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(
                        message.sender == .user
                            ? tarsAccent.opacity(0.8)
                            : Color(UIColor.secondarySystemBackground)
                    )
                    .cornerRadius(16)

                if message.requiresConfirmation, let actionId = message.actionId {
                    HStack(spacing: 16) {
                        Button("Confirm") { onConfirm?(actionId) }
                            .foregroundColor(tarsAccent)
                        Button("Deny") { onDeny?(actionId) }
                            .foregroundColor(.red)
                    }
                    .font(.system(size: 14, weight: .medium))
                    .padding(.horizontal, 14)
                }

                Text(message.timestamp, style: .time)
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 14)
            }

            if message.sender == .tars { Spacer(minLength: 60) }
        }
    }
}
