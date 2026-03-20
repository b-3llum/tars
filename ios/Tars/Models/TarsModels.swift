import Foundation

// MARK: - Request

struct TarsRequest: Codable {
    let message: String
    let context: [String: String]
    let sessionId: String?

    enum CodingKeys: String, CodingKey {
        case message, context
        case sessionId = "session_id"
    }
}

// MARK: - Response

struct TarsResponse: Codable {
    let status: String
    let response: String
    let data: [String: AnyCodable]?
    let requiresConfirmation: Bool?
    let actionId: String?
    let logs: [String]?

    enum CodingKeys: String, CodingKey {
        case status, response, data, logs
        case requiresConfirmation = "requires_confirmation"
        case actionId = "action_id"
    }
}

// MARK: - Confirm

struct ConfirmRequest: Codable {
    let actionId: String
    let confirmed: Bool

    enum CodingKeys: String, CodingKey {
        case actionId = "action_id"
        case confirmed
    }
}

// MARK: - Chat Message (local UI model)

enum MessageSender {
    case user
    case tars
}

struct ChatMessage {
    let id = UUID()
    let text: String
    let sender: MessageSender
    let timestamp = Date()
    var actionId: String?       // non-nil if confirmation is needed
    var requiresConfirmation: Bool = false
}

// MARK: - AnyCodable helper for mixed JSON values

struct AnyCodable: Codable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let str = try? container.decode(String.self) {
            value = str
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let dict = try? container.decode([String: AnyCodable].self) {
            value = dict.mapValues { $0.value }
        } else if let arr = try? container.decode([AnyCodable].self) {
            value = arr.map { $0.value }
        } else {
            value = ""
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if let str = value as? String { try container.encode(str) }
        else if let int = value as? Int { try container.encode(int) }
        else if let double = value as? Double { try container.encode(double) }
        else if let bool = value as? Bool { try container.encode(bool) }
        else { try container.encodeNil() }
    }
}
