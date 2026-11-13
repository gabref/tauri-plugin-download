import Foundation
import Tauri
import XCTest
@testable import tauri_plugin_download

final class DownloadPluginTests: XCTestCase {
   /// Exercises the real handlers and Tauri argument/response serialization.
   func testConfigureCreateListAndGetThroughPlugin() async throws {
      let directory = FileManager.default.temporaryDirectory
         .appendingPathComponent(UUID().uuidString, isDirectory: true)
      defer { try? FileManager.default.removeItem(at: directory) }
      let path = directory.appendingPathComponent("file.bin").path
      let plugin = DownloadPlugin()

      let configured = try await response(command: "configure", args: [
         "storeDir": directory.appendingPathComponent("store").path,
         "userAgent": "issue-79-simulator-spike",
      ], call: plugin.configure)
      XCTAssertNil(configured)

      let created = try await response(command: "create", args: [
         "path": path,
         "url": "https://example.com/file.bin",
         "options": ["allowMetered": false],
      ], call: plugin.create) as? [String: Any]
      let item = try XCTUnwrap(created?["download"] as? [String: Any])
      XCTAssertEqual(item["path"] as? String, path)
      XCTAssertEqual((item["options"] as? [String: Any])?["allowMetered"] as? Bool, false)

      let listed = try await response(command: "list", args: [:], call: plugin.list)
      let downloads = try XCTUnwrap(listed as? [[String: Any]])
      XCTAssertEqual(downloads.count, 1)
      XCTAssertEqual(downloads.first?["path"] as? String, path)
      XCTAssertEqual(downloads.first?["status"] as? String, "idle")
      XCTAssertTrue(downloads.first?["totalBytes"] is NSNull)

      let missing = try await response(command: "get", args: [
         "path": directory.appendingPathComponent("missing.bin").path,
      ], call: plugin.get)
      XCTAssertTrue(missing is NSNull)

      _ = try await response(command: "cancel", args: ["path": path], call: plugin.cancel)
   }

   func testMalformedArgumentsReturnNativeErrorMarker() async throws {
      let plugin = DownloadPlugin()
      let result = try await response(command: "get", args: [:], call: plugin.get)
      let marker = try XCTUnwrap((result as? [String: Any])?["__downloadError"] as? [String: Any])
      XCTAssertEqual(marker["code"] as? String, "invalid input")
   }

   /// Captures the callback from Tauri's real Invoke, without a Rust or JS caller.
   private func response(
      command: String,
      args: [String: Any],
      call: (Invoke) throws -> Void
   ) async throws -> Any? {
      let completed = expectation(description: "\(command) responds")
      completed.assertForOverFulfill = true
      var payload: String?
      let data = try JSONSerialization.data(withJSONObject: args)
      let invoke = Invoke(
         command: command, callback: 1, error: 2,
         sendResponse: { callback, value in
            XCTAssertEqual(callback, 1, "Unexpected Tauri rejection: \(value ?? "null")")
            payload = value
            completed.fulfill()
         },
         sendChannelData: { _, _ in XCTFail("Unexpected channel data") },
         data: String(decoding: data, as: UTF8.self)
      )
      try call(invoke)
      await fulfillment(of: [completed], timeout: 15)
      guard let payload else { return nil }
      return try JSONSerialization.jsonObject(with: Data(payload.utf8), options: [.fragmentsAllowed])
   }
}
