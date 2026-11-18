# BoodleBox-AI-Summit-Presentation
Repository for a presentation I gave at the 2026 AI Campu Summit hosted by BoodleBox and Lipscomb university in Nashville, TN. Created using the Reveal JS framework.

## Reveal.js presentation

Open `boodlebox-ai-summit.html` in a browser and use the arrow keys to navigate. Reveal.js and its plugins are bundled locally, along with copies of the presentation images in `images/`.

To serve it locally, run `python -m http.server` from the repository root and open `http://localhost:8000/boodlebox-ai-summit.html`.

To publish it on the web, enable GitHub Pages for the `main` branch and `/ (root)` folder in the repository settings. Once deployed, the presentation is available at `https://jhopkins77.github.io/BoodleBox-AI-Summit-Presentation/boodlebox-ai-summit.html`.

To regenerate the HTML and image copies from the PowerPoint, run `python scripts/build_reveal.py`.
