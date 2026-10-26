import SwiftUI
import UIKit

/// The system keyboard: NepaliKeyboard typing into whatever field has focus.
final class KeyboardViewController: UIInputViewController {
    private var host: UIHostingController<NepaliKeyboard>?
    private var showsGlobe: Bool?

    override func viewDidLoad() {
        super.viewDidLoad()
        let host = UIHostingController(rootView: keyboard(globe: true))
        host.view.backgroundColor = .clear
        host.sizingOptions = .intrinsicContentSize
        host.view.translatesAutoresizingMaskIntoConstraints = false
        addChild(host)
        view.addSubview(host.view)
        NSLayoutConstraint.activate([
            host.view.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            host.view.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            host.view.topAnchor.constraint(equalTo: view.topAnchor),
            host.view.bottomAnchor.constraint(equalTo: view.bottomAnchor),
        ])
        host.didMove(toParent: self)
        self.host = host
    }

    /// The globe key is only wanted where the system doesn't show its own.
    override func viewWillLayoutSubviews() {
        super.viewWillLayoutSubviews()
        if showsGlobe != needsInputModeSwitchKey {
            showsGlobe = needsInputModeSwitchKey
            host?.rootView = keyboard(globe: needsInputModeSwitchKey)
        }
    }

    private func keyboard(globe: Bool) -> NepaliKeyboard {
        NepaliKeyboard(
            purpose: .typing(
                nextKeyboard: globe ? { [weak self] in self?.advanceToNextInputMode() } : nil,
                onReturn: { [weak self] in self?.textDocumentProxy.insertText("\n") }
            ),
            insert: { [weak self] in self?.textDocumentProxy.insertText($0) },
            delete: { [weak self] in self?.textDocumentProxy.deleteBackward() }
        )
    }
}
