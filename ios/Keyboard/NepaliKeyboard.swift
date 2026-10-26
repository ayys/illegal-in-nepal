import SwiftUI

/// Colors for the keyboard: the system's look in other apps, the app's own
/// inside it.
struct KeyboardStyle {
    var background: Color
    var key: Color
    var specialKey: Color
    var text: Color
    var markText: Color

    static let system = KeyboardStyle(
        background: .clear,
        key: Color(light: .white, dark: Color(white: 0.42)),
        specialKey: Color(light: Color(red: 0.67, green: 0.69, blue: 0.73), dark: Color(white: 0.27)),
        text: .primary,
        markText: .primary
    )
}

private extension Color {
    init(light: Color, dark: Color) {
        #if canImport(UIKit)
        self.init(uiColor: UIColor { $0.userInterfaceStyle == .dark ? UIColor(dark) : UIColor(light) })
        #else
        self = light
        #endif
    }
}

/// The Nepali (Romanized) - Pro keyboard. Shift once for one shifted
/// letter; double-tap it for caps lock, the conjunct layer.
struct NepaliKeyboard: View {
    enum Purpose {
        /// A system keyboard: a 123 page, the globe, space and return.
        case typing(nextKeyboard: (() -> Void)?, onReturn: () -> Void)
        /// One अक्षर at a time: no space, return or symbols.
        case crossword
    }

    var style: KeyboardStyle = .system
    let purpose: Purpose
    /// Keys whose output this returns false for are dimmed and do nothing.
    var accepts: (String) -> Bool = { _ in true }
    let insert: (String) -> Void
    let delete: () -> Void

    private enum Shift { case off, once, locked }
    @State private var shift = Shift.off
    @State private var lastShiftTap = Date.distantPast
    @State private var symbols = false

    private var layer: NepaliLayout.Layer {
        switch shift {
        case .off: .plain
        case .once: .shift
        case .locked: .caps
        }
    }

    var body: some View {
        VStack(spacing: 10) {
            if symbols {
                ForEach(NepaliLayout.symbols, id: \.self) { row in
                    HStack(spacing: 5) {
                        ForEach(row, id: \.self) { key($0) }
                    }
                }
            } else {
                ForEach(NepaliLayout.rows, id: \.self) { row in
                    HStack(spacing: 5) {
                        ForEach(row, id: \.self) { position in
                            // Read the layer when tapped, not when drawn:
                            // a quick tap after shift can beat the redraw.
                            key(NepaliLayout.output(position, layer)) { NepaliLayout.output(position, layer) }
                        }
                    }
                }
            }
            bottomRow
        }
        .padding(.horizontal, 3)
        .padding(.top, 8)
        .padding(.bottom, 4)
        .background(style.background)
    }

    @ViewBuilder private var bottomRow: some View {
        HStack(spacing: 6) {
            switch purpose {
            case let .typing(nextKeyboard, onReturn):
                if !symbols { shiftKey }
                special(symbols ? "कखग" : "१२३", width: 52) { symbols.toggle() }
                if let nextKeyboard {
                    special(systemImage: "globe", width: 44, action: nextKeyboard)
                }
                Button {
                    insert(" ")
                } label: {
                    Text("खाली")
                        .font(.system(size: 15))
                        .frame(maxWidth: .infinity, minHeight: 42)
                }
                .buttonStyle(KeyButtonStyle(fill: style.key, text: style.text))
                deleteKey
                special(systemImage: "return", width: 56, action: onReturn)
            case .crossword:
                shiftKey
                Spacer(minLength: 0)
                deleteKey
            }
        }
    }

    /// `output` gives what the key types at the moment it's tapped.
    private func key(_ text: String, output: (() -> String)? = nil) -> some View {
        let enabled = !text.isEmpty && accepts(text)
        return Button {
            let typed = output?() ?? text
            if !typed.isEmpty && accepts(typed) {
                insert(typed)
            }
            if shift == .once { shift = .off }
        } label: {
            Text(NepaliLayout.label(text))
                .font(.system(size: text.count > 2 ? 15 : 21))
                .minimumScaleFactor(0.6)
                .lineLimit(1)
                .foregroundStyle(NepaliLayout.isMark(text) ? style.markText : style.text)
                .frame(maxWidth: .infinity, minHeight: 42)
        }
        .buttonStyle(KeyButtonStyle(fill: style.key, text: style.text))
        .disabled(!enabled)
        .opacity(enabled ? 1 : 0.35)
        .accessibilityLabel(text)
    }

    private var shiftKey: some View {
        special(systemImage: shift == .locked ? "capslock.fill" : shift == .once ? "shift.fill" : "shift",
                width: 48, highlighted: shift != .off) {
            let now = Date()
            if now.timeIntervalSince(lastShiftTap) < 0.35 {
                shift = .locked
            } else {
                shift = shift == .off ? .once : .off
            }
            lastShiftTap = now
        }
        .accessibilityLabel(shift == .locked ? "संयुक्ताक्षर" : "सिफ्ट")
    }

    private var deleteKey: some View {
        RepeatingKey(fill: style.specialKey, text: style.text, action: delete) {
            Image(systemName: "delete.left").font(.system(size: 18))
        }
        .frame(width: 48)
        .accessibilityLabel("मेटाउनुहोस्")
    }

    private func special(_ title: String = "", systemImage: String? = nil, width: CGFloat,
                         highlighted: Bool = false, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Group {
                if let systemImage {
                    Image(systemName: systemImage).font(.system(size: 18))
                } else {
                    Text(title).font(.system(size: 15))
                }
            }
            .frame(width: width, height: 42)
        }
        .buttonStyle(KeyButtonStyle(fill: highlighted ? style.key : style.specialKey, text: style.text))
    }
}

struct KeyButtonStyle: ButtonStyle {
    let fill: Color
    let text: Color

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(text)
            .background(
                RoundedRectangle(cornerRadius: 6, style: .continuous)
                    .fill(fill)
                    .brightness(configuration.isPressed ? -0.12 : 0)
                    .shadow(color: .black.opacity(0.3), radius: 0, x: 0, y: 1)
            )
            .contentShape(Rectangle())
    }
}

/// Fires once on touch, then repeats while held, like the system delete key.
struct RepeatingKey<Label: View>: View {
    let fill: Color
    let text: Color
    let action: () -> Void
    @ViewBuilder let label: () -> Label
    @State private var repeating: Task<Void, Never>?

    var body: some View {
        label()
            .foregroundStyle(text)
            .frame(maxWidth: .infinity, minHeight: 42)
            .background(
                RoundedRectangle(cornerRadius: 6, style: .continuous)
                    .fill(fill)
                    .brightness(repeating == nil ? 0 : -0.12)
                    .shadow(color: .black.opacity(0.3), radius: 0, x: 0, y: 1)
            )
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { _ in
                        guard repeating == nil else { return }
                        action()
                        repeating = Task { @MainActor in
                            try? await Task.sleep(for: .milliseconds(450))
                            while !Task.isCancelled {
                                action()
                                try? await Task.sleep(for: .milliseconds(80))
                            }
                        }
                    }
                    .onEnded { _ in
                        repeating?.cancel()
                        repeating = nil
                    }
            )
            .accessibilityAddTraits(.isButton)
            .accessibilityAction { action() }
    }
}
