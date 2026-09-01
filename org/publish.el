;;; publish.el --- Export Denote blog notes to site/blog/  -*- lexical-binding: t; -*-

(require 'cl-lib)
(require 'ox-publish)
(require 'subr-x)

(defvar blog-root
  (expand-file-name ".." (file-name-directory (or load-file-name
                                                  buffer-file-name)))
  "Repository root (parent of the org/ silo).")

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
   "<link rel=\"icon\" href=\"/assets/favicon.ico\" type=\"image/x-icon\">\n"
   "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n"
   "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>\n"
   "<link rel=\"preload\" href=\"https://fonts.googleapis.com/css2?family=Poppins&display=swap\" as=\"style\" onload=\"this.onload=null;this.rel='stylesheet'\">\n"
   "<noscript><link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=Poppins&display=swap\"></noscript>\n"
   "<link rel=\"stylesheet\" href=\"/common.css\">\n"
   "<style>\n"
   "body { font-family: 'Poppins', serif; }\n"
   ".blog-nav { margin-bottom: 1.5rem; }\n"
   ".blog-meta { color: #666; margin-top: 2rem; }\n"
   ".blog-index { list-style: none; padding: 0; }\n"
   ".blog-index li { margin: 0.75rem 0; }\n"
   ".blog-index time { color: #666; margin-left: 0.75rem; font-size: 0.9rem; }\n"
   "pre { background: #f5f5f5; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; }\n"
   "img { max-width: 100%; height: auto; }\n"
   "@media (prefers-color-scheme: dark) {\n"
   "  .blog-meta, .blog-index time { color: #999; }\n"
   "  pre { background: #1e1e1e; }\n"
   "}\n"
   "</style>\n"))

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

(setq org-export-with-toc nil
      org-export-with-section-numbers nil
      org-html-doctype "html5"
      org-html-html5-fancy t
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
         :publishing-function org-html-publish-to-html
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
