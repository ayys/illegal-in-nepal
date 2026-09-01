;;; Directory Local Variables
;;; For more information see (info "(emacs) Directory Variables")
;;;
;;; This directory is a Denote silo for public blog notes.
;;; First visit may prompt about unsafe local variables; allow them.

((nil . ((eval . (setq-local denote-directory
                             (expand-file-name
                              (locate-dominating-file default-directory
                                                      ".dir-locals.el")))))))
