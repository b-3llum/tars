import Foundation

final class NetworkManager {

    static let shared = NetworkManager()

    // MARK: - Configuration (update these for your environment)

    private let baseURL = "http://192.168.1.10:8400/tars"  // Control server address
    private let apiKey  = "change-me-to-a-secure-random-string"

    private let session: URLSession
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        session = URLSession(configuration: config)
    }

    // MARK: - Public API

    /// Send a message to TARS and get a response.
    func sendRequest(message: String, context: [String: String] = [:],
                     completion: @escaping (Result<TarsResponse, TarsError>) -> Void) {

        let body = TarsRequest(message: message, context: context, sessionId: nil)
        post(path: "/request", body: body, completion: completion)
    }

    /// Confirm or deny a pending action.
    func confirm(actionId: String, confirmed: Bool,
                 completion: @escaping (Result<TarsResponse, TarsError>) -> Void) {

        let body = ConfirmRequest(actionId: actionId, confirmed: confirmed)
        post(path: "/confirm", body: body, completion: completion)
    }

    /// Check server health.
    func healthCheck(completion: @escaping (Bool) -> Void) {
        guard let url = URL(string: baseURL + "/health") else {
            completion(false)
            return
        }

        var request = URLRequest(url: url)
        request.addValue(apiKey, forHTTPHeaderField: "X-API-Key")

        session.dataTask(with: request) { data, response, error in
            guard error == nil,
                  let http = response as? HTTPURLResponse,
                  http.statusCode == 200 else {
                completion(false)
                return
            }
            completion(true)
        }.resume()
    }

    // MARK: - Private

    private func post<T: Encodable>(path: String, body: T,
                                     completion: @escaping (Result<TarsResponse, TarsError>) -> Void) {
        guard let url = URL(string: baseURL + path) else {
            completion(.failure(.invalidURL))
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.addValue(apiKey, forHTTPHeaderField: "X-API-Key")

        do {
            request.httpBody = try encoder.encode(body)
        } catch {
            completion(.failure(.encoding(error)))
            return
        }

        session.dataTask(with: request) { [decoder] data, response, error in
            if let error = error {
                completion(.failure(.network(error)))
                return
            }

            guard let http = response as? HTTPURLResponse else {
                completion(.failure(.unknown))
                return
            }

            guard (200...299).contains(http.statusCode) else {
                completion(.failure(.httpError(http.statusCode)))
                return
            }

            guard let data = data else {
                completion(.failure(.noData))
                return
            }

            do {
                let tarsResponse = try decoder.decode(TarsResponse.self, from: data)
                completion(.success(tarsResponse))
            } catch {
                completion(.failure(.decoding(error)))
            }
        }.resume()
    }
}

// MARK: - Error

enum TarsError: Error, LocalizedError {
    case invalidURL
    case encoding(Error)
    case network(Error)
    case httpError(Int)
    case noData
    case decoding(Error)
    case unknown

    var errorDescription: String? {
        switch self {
        case .invalidURL:         return "Invalid server URL"
        case .encoding(let e):    return "Encoding error: \(e.localizedDescription)"
        case .network(let e):     return "Network error: \(e.localizedDescription)"
        case .httpError(let code): return "Server returned HTTP \(code)"
        case .noData:             return "No data in response"
        case .decoding(let e):    return "Decoding error: \(e.localizedDescription)"
        case .unknown:            return "Unknown error"
        }
    }
}
