Web Browser Project
=======================

This repository contains the code for my personal web browser project. The browser is built using Python, dukpy, and Tkinter, focusing on handling text-based web pages.


Fetures
-------

- Rendering Engine: Custom rendering engine that handles HTML parsing, CSS parsing, layout, styling, and drawing text.
- User Interface: Chrome-like interface with support for tabs, bookmarks, and search history.
- JavaScript DOM API: Implemented a subset of the JavaScript DOM API for text-based interactions.
- Security: Privacy and security features, including cookie and login management, XSS, and CSRF protection.

Setup
-----


Clone this repository to your computer:

```bash

git clone https://github.com/yourusername/new-project.git
cd new-project

```

Work
----

The main implementation of the web browser can be found in browser.py. The browser is modular, and you can find different parts of the implementation in separate files:

- `http.py`: Handling HTTP requests and responses.
- `ui.py`: User interface components.
- `layout.py`: Layout engine for rendering HTML and CSS.
- `CSSParser.py`: Parsing CSS files.
- `HTMLParser.py`: Parsing HTML files.
- `Element.py`: Handling HTML elements.
- `Text.py`: Handling text nodes.
- `helpers.py`: Utility functions.
- `classselector.py`: Handling CSS class selectors.
- `DescendantSelector.py`: Handling CSS descendant selectors.
- `TagSelector.py`: Handling CSS tag selectors.
- `draw.py`: Drawing graphics on the screen.
- `tab.py`: Managing browser tabs.
- `server.py`: Running a local web server for testing.

___Additional files include:___

- `.github`: GitHub workflows and configurations.
- `.idea`: IDE configurations.
- `local_files`: Local files for testing.
- `openmoji`: Emoji support.
- `test`: Test cases.
- `__pycache__`: Python cache files.
- `.gitignore`: Git ignore file.
- `.gitmodules `: Git submodules configuration.
- `browser.css`: CSS file for the browser.
- `comment.css`: CSS file for comments.
- `comment.js`: JavaScript file for comments.
- `output.txt`: Output file for logging.
- `README.md`: This readme file.
- `runtime.js`: JavaScript runtime file.
- `test.js`: JavaScript test file.

Running the Browser
-------------------

To run the browser, execture the following command:

```bash 
python browser.py
```

