;;; publish.el --- Export Denote blog notes to site/blog/  -*- lexical-binding: t; -*-

(require 'cl-lib)
(require 'org-element)
(require 'ox-publish)
(require 'subr-x)

(defvar blog-root
  (expand-file-name ".." (file-name-directory (or load-file-name
                                                  buffer-file-name)))
  "Repository root (parent of the org/ silo).")

(defvar blog-lisp-dir
  (expand-file-name "lisp" (file-name-directory (or load-file-name
                                                   buffer-file-name)))
  "Vendored Elisp loaded during `emacs -Q' publish (htmlize, gleam-ts-mode).")

(add-to-list 'load-path blog-lisp-dir)
(require 'htmlize)
(when (and (>= emacs-major-version 29)
           (require 'treesit nil t)
           (require 'gleam-ts-mode nil t))
  (unless (treesit-ready-p 'gleam)
    (gleam-ts-install-grammar))
  (when (treesit-ready-p 'gleam)
    (add-to-list 'org-src-lang-modes '("gleam" . gleam-ts))))

;; Faces used by htmlize.  emacs -Q has no theme, so these have to
;; be set here or the spans ship without colors.
(custom-set-faces
 '(default ((t (:foreground "#2c1810" :background "#fff1dc"))))
 '(font-lock-keyword-face ((t (:foreground "#b03a22"))))
 '(font-lock-builtin-face ((t (:foreground "#b03a22"))))
 '(font-lock-string-face ((t (:foreground "#9a4a1a"))))
 '(font-lock-comment-face ((t (:foreground "#8a6456" :slant italic))))
 '(font-lock-comment-delimiter-face ((t (:foreground "#8a6456" :slant italic))))
 '(font-lock-function-name-face ((t (:foreground "#e07a3a"))))
 '(font-lock-type-face ((t (:foreground "#7a3d8c"))))
 '(font-lock-constant-face ((t (:foreground "#7a3d8c"))))
 '(font-lock-variable-name-face ((t (:foreground "#2c1810"))))
 '(font-lock-property-name-face ((t (:foreground "#8a6456"))))
 '(font-lock-delimiter-face ((t (:foreground "#8a6456"))))
 '(font-lock-bracket-face ((t (:foreground "#8a6456"))))
 '(font-lock-operator-face ((t (:foreground "#8a6456"))))
 '(gleam-ts-constructor-face ((t (:foreground "#7a3d8c"))))
 '(gleam-ts-module-face ((t (:foreground "#7a3d8c")))))

(defvar blog-org-dir (expand-file-name "org" blog-root))
(defvar blog-out-dir (expand-file-name "site/blog" blog-root))

(defun blog--org-keyword (file keyword)
  "Return the first #+KEYWORD value from FILE, or nil."
  (with-temp-buffer
    (insert-file-contents file)
    (goto-char (point-min))
    (when (re-search-forward
           (format "^#\\+%s:[ \t]*\\(.*\\)$" (regexp-quote keyword))
           nil t)
      (string-trim (match-string 1)))))

(defun blog--filename-keywords (filename)
  "Return Denote keywords from FILENAME."
  (let ((base (file-name-nondirectory filename)))
    (when (string-match "__\\([^.]+\\)\\." base)
      (split-string (match-string 1 base) "_" t))))

(defun blog-public-p (filename)
  "Return non-nil if FILENAME is a public blog note.
Public notes have the `blog' keyword and do not have `draft'."
  (let ((keywords (blog--filename-keywords filename)))
    (and (member "blog" keywords)
         (not (member "draft" keywords)))))

(defun blog-public-files ()
  "Absolute paths of public blog Org files in the silo."
  (cl-remove-if-not #'blog-public-p
                    (directory-files blog-org-dir t "\\.org$")))

(defun blog--identifier (file)
  "Denote identifier of FILE, used for newest-first sorting."
  (or (blog--org-keyword file "identifier")
      (let ((base (file-name-nondirectory file)))
        (if (string-match "\\`\\([0-9]\\{8\\}T[0-9]\\{6\\}\\)" base)
            (match-string 1 base)
          ""))))

(defun blog--slug (file)
  "Public URL slug for FILE (EXPORT_FILE_NAME, without extension)."
  (let* ((name (blog--org-keyword file "EXPORT_FILE_NAME"))
         (name (and name (string-trim name)))
         (name (and name
                    (replace-regexp-in-string "\\.\\(html\\|org\\)\\'"
                                              "" name))))
    (if (and name (not (string-empty-p name)))
        name
      (file-name-base file))))

(defun blog--display-date (date-string)
  "Extract YYYY-MM-DD from a Denote/Org DATE-STRING."
  (if (and date-string
           (string-match "\\([0-9]\\{4\\}-[0-9]\\{2\\}-[0-9]\\{2\\}\\)"
                         date-string))
      (match-string 1 date-string)
    (or date-string "")))

(defun blog--html-escape (s)
  "Escape S for HTML text."
  (setq s (or s ""))
  (dolist (pair '(("&" . "&amp;") ("<" . "&lt;") (">" . "&gt;")
                  ("\"" . "&quot;")))
    (setq s (replace-regexp-in-string (car pair) (cdr pair) s t t)))
  s)

(defconst blog-html-head
  (concat
   "<meta name=\"color-scheme\" content=\"only light\">\n"
   "<link rel=\"icon\" href=\"/assets/favicon.ico\" type=\"image/x-icon\">\n"
   "<link rel=\"stylesheet\" href=\"/common.css\">\n"))

(defconst blog-preamble
  (concat
   "<nav class=\"blog-nav\">"
   "<a href=\"/\">गृह</a> · <a href=\"/blog/\">ब्लग</a>"
   "</nav>\n"))

(defun blog-write-index (_project)
  "Write site/blog/index.html listing public posts, newest first."
  (let* ((posts
          (mapcar (lambda (file)
                    (list :title (or (blog--org-keyword file "title")
                                     (file-name-base file))
                          :date (blog--display-date
                                 (blog--org-keyword file "date"))
                          :slug (blog--slug file)
                          :id (blog--identifier file)))
                  (blog-public-files)))
         (sorted (cl-sort posts #'string> :key (lambda (p) (plist-get p :id))))
         (items
          (mapconcat
           (lambda (p)
             (format
              "<li><a href=\"/blog/%s.html\">%s</a><time datetime=\"%s\">%s</time></li>\n"
              (blog--html-escape (plist-get p :slug))
              (blog--html-escape (plist-get p :title))
              (blog--html-escape (plist-get p :date))
              (blog--html-escape (plist-get p :date))))
           sorted
           "")))
    (make-directory blog-out-dir t)
    (with-temp-file (expand-file-name "index.html" blog-out-dir)
      (insert
       "<!DOCTYPE html>\n"
       "<html lang=\"ne\">\n"
       "<head>\n"
       "<meta charset=\"UTF-8\">\n"
       "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
       "<title>ब्लग | आयुष झा</title>\n"
       blog-html-head
       "</head>\n"
       "<body>\n"
       blog-preamble
       "<h1>ब्लग</h1>\n"
       "<ul class=\"blog-index\">\n"
       items
       "</ul>\n"
       "</body>\n"
       "</html>\n"))
    (message "Wrote %s (%d posts)"
             (expand-file-name "index.html" blog-out-dir)
             (length sorted))))

(defun blog--output-label-p (el)
  "Return non-nil if EL is a short paragraph like \"output:\"."
  (when (eq (org-element-type el) 'paragraph)
    (string-match-p "\\`outputs?:\\'"
                    (string-trim (org-element-interpret-data el)))))

(defun blog--result-block-p (el)
  "Return non-nil if EL is a babel result (example or fixed-width)."
  (memq (org-element-type el) '(example-block fixed-width)))

(defun blog--pair-src-and-results-list (elements)
  "Wrap a src-block followed by its result in `src-with-result' special-blocks.
A paragraph that is only \"output:\" or \"outputs:\" between the two is dropped."
  (let (out)
    (while elements
      (let ((el (car elements))
            (rest (cdr elements)))
        (if (and (eq (org-element-type el) 'src-block) rest)
            (let* ((n1 (car rest))
                   (labeled (blog--output-label-p n1))
                   (result (if labeled (cadr rest) n1)))
              (if (blog--result-block-p result)
                  (progn
                    (push (org-element-create
                           'special-block
                           '(:type "src-with-result")
                           el
                           (org-element-create
                            'special-block
                            '(:type "src-result")
                            result))
                          out)
                    (setq elements (nthcdr (if labeled 2 1) rest)))
                (push el out)
                (setq elements rest)))
          (push el out)
          (setq elements rest))))
    (nreverse out)))

(defun blog--pair-src-and-results-in (parent)
  "Recursively pair source blocks with following results under PARENT."
  (when (and (memq (org-element-type parent) org-element-greater-elements)
             (not (memq (org-element-type parent) '(table property-drawer)))
             (org-element-contents parent))
    (dolist (child (org-element-contents parent))
      (blog--pair-src-and-results-in child))
    (apply #'org-element-set-contents
           parent
           (blog--pair-src-and-results-list
            (org-element-contents parent)))))

(defun blog--number-src-blocks (tree)
  "Give every source block `-n' line numbers unless it already has them."
  (org-element-map tree 'src-block
    (lambda (src)
      (unless (org-element-property :number-lines src)
        (org-element-put-property src :number-lines '(new . 0)))))
  tree)

(defun blog--pair-src-and-results (tree backend _info)
  "Parse-tree filter: group `:exports both' source + result for HTML."
  (when (org-export-derived-backend-p backend 'html)
    (blog--pair-src-and-results-in tree)
    (blog--number-src-blocks tree))
  tree)

(add-to-list 'org-export-filter-parse-tree-functions
             #'blog--pair-src-and-results)

(defun blog--html-linenr-gutter (html backend _info)
  "Strip selectable \"N:\" text from line-number spans."
  (if (org-export-derived-backend-p backend 'html)
      (replace-regexp-in-string
       "<span class=\"linenr\">[ 0-9]+: </span>"
       "<span class=\"linenr\" aria-hidden=\"true\"></span>"
       html t t)
    html))

(add-to-list 'org-export-filter-final-output-functions
             #'blog--html-linenr-gutter)

(defun blog--result-label (info)
  "Return the output label for the current export language in INFO."
  (if (equal (plist-get info :language) "ne") "नतिजा" "Output"))

(defun blog--trim-example-pre (html)
  "Drop the leading newline Org puts inside <pre class=\"example\">."
  (replace-regexp-in-string
   "\\`<pre class=\"example\">\n"
   "<pre class=\"example\">"
   (or html "") t t))

(defun blog-html-special-block (special-block contents info)
  "Transcode SPECIAL-BLOCK to HTML, with a labeled result under source."
  (let ((type (org-element-property :type special-block))
        (contents (or contents "")))
    (cond
     ((equal type "src-with-result")
      (format "<div class=\"src-with-result\">\n%s</div>" contents))
     ((equal type "src-result")
      (format
       "<div class=\"src-result\"><p class=\"src-result-label\">%s</p>\n%s</div>"
       (blog--result-label info)
       (blog--trim-example-pre contents)))
     (t
      (org-html-special-block special-block contents info)))))

(org-export-define-derived-backend 'blog-html 'html
  :translate-alist '((special-block . blog-html-special-block)))

(defun blog-html-publish-to-html (plist filename pub-dir)
  "Publish FILENAME as HTML using the blog-html backend."
  (org-publish-org-to 'blog-html filename
                      (concat (when (> (length org-html-extension) 0) ".")
                              (or (plist-get plist :html-extension)
                                  org-html-extension
                                  "html"))
                      plist pub-dir))

;; Include cached #+RESULTS with the source.  Do not re-run blocks
;; at publish time (CI has no Gleam/project cwd).
(setq org-babel-default-header-args
      (cons '(:exports . "both")
            (assq-delete-all :exports org-babel-default-header-args)))
(setq org-babel-default-header-args
      (cons '(:eval . "never-export")
            (assq-delete-all :eval org-babel-default-header-args)))

(setq org-export-with-toc nil
      org-export-with-section-numbers nil
      org-html-doctype "html5"
      org-html-html5-fancy t
      org-html-htmlize-output-type (if (featurep 'htmlize) 'inline-css nil)
      org-html-head-include-default-style nil
      org-html-head-include-scripts nil
      org-html-validation-link nil
      org-html-viewport '((width "device-width")
                          (initial-scale "1")
                          (maximum-scale "")
                          (minimum-scale "")
                          (user-scalable ""))
      org-publish-use-timestamps-flag nil
      org-publish-project-alist
      `(("blog-posts"
         :base-directory ,blog-org-dir
         :base-extension "org"
         :publishing-directory ,blog-out-dir
         :recursive nil
         :exclude ".*"
         :include ,(mapcar #'file-name-nondirectory (blog-public-files))
         :publishing-function blog-html-publish-to-html
         :section-numbers nil
         :with-toc nil
         :with-author t
         :with-date t
         :with-creator nil
         :time-stamp-file nil
         :html-head ,blog-html-head
         :html-preamble ,blog-preamble
         :html-postamble "<p class=\"blog-meta\">%a · %d</p>"
         :completion-function blog-write-index)
        ("blog" :components ("blog-posts"))))

(make-directory blog-out-dir t)
(let ((files (blog-public-files)))
  (if files
      (progn
        (dolist (f files)
          (message "Publishing %s → /blog/%s.html"
                   (file-name-nondirectory f)
                   (blog--slug f)))
        (org-publish "blog" t))
    (message "No public blog notes found in %s" blog-org-dir)
    (blog-write-index nil)))
