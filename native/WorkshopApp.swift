import AppKit
import WebKit

// A local window over the existing workshop server. No embedded browser service,
// remote application content, or separate learner database is introduced.
final class WorkshopApp: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    private let home = URL(string: "http://127.0.0.1:7318/")!
    private var window: NSWindow!
    private var webView: WKWebView!
    private var status: NSStackView!
    private var statusLabel: NSTextField!
    private var starting = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.appearance = NSAppearance(named: .aqua)
        makeMenu()
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1320, height: 880),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = "Engineering Workshop"
        window.minSize = NSSize(width: 760, height: 560)
        window.isReleasedWhenClosed = false
        window.setFrameAutosaveName("WorkshopWindow")
        window.center()
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsBackForwardNavigationGestures = true
        webView.translatesAutoresizingMaskIntoConstraints = false
        let content = window.contentView!
        content.addSubview(webView)
        NSLayoutConstraint.activate([
            webView.leadingAnchor.constraint(equalTo: content.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: content.trailingAnchor),
            webView.topAnchor.constraint(equalTo: content.topAnchor),
            webView.bottomAnchor.constraint(equalTo: content.bottomAnchor)
        ])
        statusLabel = NSTextField(wrappingLabelWithString: "Starting Engineering Workshop…")
        statusLabel.font = .systemFont(ofSize: 18, weight: .medium)
        statusLabel.alignment = .center
        let retry = NSButton(title: "Open workshop", target: self, action: #selector(startWorkshop))
        status = NSStackView(views: [statusLabel, retry])
        status.orientation = .vertical
        status.spacing = 18
        status.translatesAutoresizingMaskIntoConstraints = false
        content.addSubview(status)
        NSLayoutConstraint.activate([
            status.centerXAnchor.constraint(equalTo: content.centerXAnchor),
            status.centerYAnchor.constraint(equalTo: content.centerYAnchor),
            status.widthAnchor.constraint(lessThanOrEqualToConstant: 520)
        ])
        showWindow()
        startWorkshop()
    }

    private func makeMenu() {
        let bar = NSMenu()
        let application = NSMenuItem(); bar.addItem(application)
        let appMenu = NSMenu(); application.submenu = appMenu
        appMenu.addItem(withTitle: "About Engineering Workshop", action: #selector(about), keyEquivalent: "").target = self
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Hide Engineering Workshop", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(withTitle: "Quit Engineering Workshop", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let file = NSMenuItem(); bar.addItem(file); file.submenu = NSMenu(title: "File")
        file.submenu!.addItem(withTitle: "Open Workshop", action: #selector(showWindow), keyEquivalent: "0").target = self
        file.submenu!.addItem(withTitle: "Open in Browser", action: #selector(openInBrowser), keyEquivalent: "b").target = self
        file.submenu!.addItem(withTitle: "Close Window", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        let edit = NSMenuItem(); bar.addItem(edit); edit.submenu = NSMenu(title: "Edit")
        for (title, action, key) in [("Undo", "undo:", "z"), ("Cut", "cut:", "x"), ("Copy", "copy:", "c"), ("Paste", "paste:", "v"), ("Select All", "selectAll:", "a")] {
            edit.submenu!.addItem(withTitle: title, action: Selector(action), keyEquivalent: key)
        }
        let view = NSMenuItem(); bar.addItem(view); view.submenu = NSMenu(title: "View")
        view.submenu!.addItem(withTitle: "Reload Workshop", action: #selector(startWorkshop), keyEquivalent: "r").target = self
        let windows = NSMenuItem(); bar.addItem(windows); windows.submenu = NSMenu(title: "Window")
        windows.submenu!.addItem(withTitle: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        windows.submenu!.addItem(withTitle: "Zoom", action: #selector(NSWindow.performZoom(_:)), keyEquivalent: "")
        NSApp.windowsMenu = windows.submenu
        NSApp.mainMenu = bar
    }

    @objc private func showWindow() {
        window?.deminiaturize(nil)
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        showWindow(); return true
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
    @objc private func about() {
        NSApp.orderFrontStandardAboutPanel(options: [.applicationName: "Engineering Workshop", .applicationVersion: "1.0", .credits: NSAttributedString(string: "ML and software engineering lessons that run on this Mac.\nLessons, books and progress stay on this Mac.")])
    }
    @objc private func openInBrowser() { NSWorkspace.shared.open(webView.url.flatMap { isLocal($0) ? $0 : nil } ?? home) }
    private func isLocal(_ url: URL) -> Bool { url.scheme == "http" && url.host == "127.0.0.1" && url.port == 7318 }

    @objc private func startWorkshop() {
        guard !starting else { return }
        starting = true
        statusLabel.stringValue = "Starting Engineering Workshop…"
        status.isHidden = false
        guard let path = Bundle.main.object(forInfoDictionaryKey: "WorkshopRoot") as? String else {
            showError("Reinstall the app: run Install Mac App.command in the project folder."); return
        }
        let root = URL(fileURLWithPath: path)
        let process = Process()
        process.executableURL = root.appendingPathComponent(".venv/bin/python")
        process.arguments = [root.appendingPathComponent("scripts/launch.py").path, "--no-open"]
        process.currentDirectoryURL = root
        let output = Pipe(); process.standardOutput = output; process.standardError = output
        process.terminationHandler = { [weak self] task in
            let data = output.fileHandleForReading.readDataToEndOfFile()
            DispatchQueue.main.async {
                guard let self else { return }
                self.starting = false
                if task.terminationStatus == 0 {
                    let target = self.webView.url.flatMap { self.isLocal($0) ? $0 : nil } ?? self.home
                    self.webView.load(URLRequest(url: target))
                } else {
                    self.showError("Could not start Engineering Workshop. Run Setup ML Workshop.command in the project folder, then try again.\n\n" + String((String(data: data, encoding: .utf8) ?? "").suffix(800)))
                }
            }
        }
        do { try process.run() } catch { showError("Run Setup ML Workshop.command in the project folder first.\n\n" + error.localizedDescription) }
    }
    private func showError(_ message: String) { starting = false; statusLabel.stringValue = message; status.isHidden = false }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) { status.isHidden = true }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { showError(error.localizedDescription) }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { showError(error.localizedDescription) }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        if isLocal(url) {
            decisionHandler(action.shouldPerformDownload ? .download : .allow)
        } else if action.targetFrame?.isMainFrame == false && url.scheme == "about" {
            decisionHandler(.allow)
        } else {
            decisionHandler(.cancel)
            if ["https", "http"].contains(url.scheme ?? "") { NSWorkspace.shared.open(url) }
        }
    }
    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        let disposition = (response.response as? HTTPURLResponse)?.value(forHTTPHeaderField: "Content-Disposition") ?? ""
        decisionHandler(disposition.lowercased().hasPrefix("attachment") || !response.canShowMIMEType ? .download : .allow)
    }
    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = action.request.url {
            if isLocal(url) { webView.load(action.request) }
            else if ["http", "https"].contains(url.scheme ?? "") { NSWorkspace.shared.open(url) }
        }
        return nil
    }
    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) { download.delegate = self }
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) { download.delegate = self }
    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
        let panel = NSSavePanel(); panel.nameFieldStringValue = suggestedFilename
        panel.beginSheetModal(for: window) { result in completionHandler(result == .OK ? panel.url : nil) }
    }
    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        let alert = NSAlert(); alert.messageText = "Download could not be saved"; alert.informativeText = error.localizedDescription
        alert.beginSheetModal(for: window)
    }
}

let application = NSApplication.shared
let delegate = WorkshopApp()
application.delegate = delegate
application.run()
