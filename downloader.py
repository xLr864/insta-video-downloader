from flask import Flask, request, render_template_string, send_file, after_this_request
from io import BytesIO
import re, os, uuid, shutil
import instaloader

app = Flask(__name__)
app.config['SESSION_COOKIE_NAME'] = 'insta_downloader_session'  # Avoid default huge session name

HTML = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>Instagram Video Downloader</title>
  <style>
    html, body {
      overflow-x: hidden;
      overflow-y: auto;
    }

    :root {
      --bg-color: #f2f2f2;
      --text-color: #000;
      --container-bg: #fff;
      --input-bg: #f5f5f5;
      --toggle-track: #ccc;
      --toggle-thumb: #fff;
    }

    body.dark-mode {
      --bg-color: #121212;
      --text-color: #fff;
      --container-bg: #1e1e1e;
      --input-bg: #2c2c2c;
      --toggle-track: #666;
      --toggle-thumb: #222;
    }

    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background: var(--bg-color);
      color: var(--text-color);
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      margin: 0;
      transition: background 0.6s ease-in-out, color 0.6s ease-in-out;
      position: relative;
    }

    .transition-circle {
      position: fixed;
      border-radius: 50%;
      background: var(--bg-color);
      width: 0;
      height: 0;
      transform: translate(-50%, -50%);
      z-index: 0;
      pointer-events: none;
    }

    .container {
      background: var(--container-bg);
      padding: 2em;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      text-align: center;
      width: 90%;
      max-width: 500px;
      transition: background 0.6s, color 0.6s;
      z-index: 1;
      position: relative;
    }

    body.fade-light .container {
      animation: containerFadeLight 0.6s ease-in-out;
    }

    body.fade-dark .container {
      animation: containerFadeDark 0.6s ease-in-out;
    }

    @keyframes containerFadeLight {
      0% {
        background-color: #1e1e1e;
        color: #fff;
      }
      100% {
        background-color: #fff;
        color: #000;
      }
    }

    @keyframes containerFadeDark {
      0% {
        background-color: #fff;
        color: #000;
      }
      100% {
        background-color: #1e1e1e;
        color: #fff;
      }
    }

    input[type=text] {
      width: 90%;
      padding: 10px;
      margin: 1em 0;
      border-radius: 8px;
      border: 1px solid #ccc;
      font-size: 16px;
      background: var(--input-bg);
      color: gray;
      transition: background 0.3s;
    }

    input[type=submit] {
      padding: 10px 20px;
      border: none;
      background-color: #0095f6;
      color: white;
      border-radius: 8px;
      font-size: 16px;
      cursor: pointer;
      transition: background 0.3s;
    }

    .theme-switch {
      position: absolute;
      top: 20px;
      right: 20px;
      z-index: 2;
    }

    .switch {
      position: relative;
      display: inline-block;
      width: 60px;
      height: 34px;
    }

    .switch input { display: none; }

    .slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: var(--toggle-track);
      transition: .4s;
      border-radius: 34px;
    }

    .slider:before {
      position: absolute;
      content: "🌙";
      height: 26px;
      width: 26px;
      left: 4px;
      bottom: 4px;
      background-color: var(--toggle-thumb);
      transition: .4s;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
    }

    input:checked + .slider {
      background-color: var(--toggle-track);
    }

    input:checked + .slider:before {
      transform: translateX(26px);
      content: "☀️";
    }

    .error {
      color: red;
      margin-top: 1em;
    }
  </style>
</head>
<body>
  <div class=\"transition-circle\" id=\"circle\"></div>
  <div class=\"theme-switch\">
    <label class=\"switch\">
      <input type=\"checkbox\" id=\"themeToggle\" onclick=\"toggleDarkMode(event)\">
      <span class=\"slider\"></span>
    </label>
  </div>
  <div class=\"container\">
    <h2>Instagram Video Downloader</h2>
    <form method=post>
      <input type=text name=url placeholder=\"Paste Instagram post URL here\" required>
      <br>
      <input type=submit value=\"Download Video\">
    </form>
    {% if error %}
      <div class=\"error\">{{ error }}</div>
    {% endif %}
  </div>

  <script>
    const toggleCheckbox = document.getElementById('themeToggle');
    if (localStorage.getItem('darkMode') === 'true') {
      document.body.classList.add('dark-mode');
      toggleCheckbox.checked = true;
    }

    function toggleDarkMode(event) {
      const circle = document.getElementById('circle');
      const x = event.clientX;
      const y = event.clientY;

      circle.style.left = `${x}px`;
      circle.style.top = `${y}px`;
      circle.style.transition = 'none';
      circle.style.width = '0';
      circle.style.height = '0';

      const wasDark = document.body.classList.contains('dark-mode');

      requestAnimationFrame(() => {
        circle.style.transition = 'width 0.6s ease-out, height 0.6s ease-out';
        circle.style.width = '3000px';
        circle.style.height = '3000px';
      });

      setTimeout(() => {
        if (wasDark) {
          document.body.classList.remove('dark-mode');
          document.body.classList.add('fade-light');
          setTimeout(() => document.body.classList.remove('fade-light'), 600);
        } else {
          document.body.classList.add('fade-dark');
          setTimeout(() => {
            document.body.classList.remove('fade-dark');
            document.body.classList.add('dark-mode');
          }, 0);
        }
        localStorage.setItem('darkMode', !wasDark);
      }, 150);

      setTimeout(() => {
        circle.style.transition = 'none';
        circle.style.width = '0';
        circle.style.height = '0';
      }, 1000);
    }
  </script>
</body>
</html>
"""

def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "_", title)

@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    if request.method == 'POST':
        url = request.form['url'].strip()
        try:
            if "instagram.com" not in url:
                raise Exception("Please enter a valid Instagram URL.")

            shortcode = url.strip("/").split("/")[-1]
            folder = f"temp_{uuid.uuid4()}"
            os.mkdir(folder)
            cwd = os.getcwd()
            os.chdir(folder)

            loader = instaloader.Instaloader(dirname_pattern='.', save_metadata=False, download_comments=False)
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            loader.download_post(post, target='')

            os.chdir(cwd)

            post_dir = os.path.join(folder, "")
            video_file = None
            for file in os.listdir(post_dir):
                if file.endswith(".mp4"):
                    video_file = os.path.join(post_dir, file)
                    break

            if not video_file:
                raise Exception("No video found in the Instagram post.")

            with open(video_file, 'rb') as f:
                buffer = BytesIO(f.read())
            buffer.seek(0)

            filename = sanitize_filename(post.caption[:80] or "instagram_video") + ".mp4"

            @after_this_request
            def remove_folder(response):
                shutil.rmtree(folder)
                return response

            return send_file(buffer, as_attachment=True, download_name=filename, mimetype='video/mp4')

        except Exception as e:
            error = str(e)

    return render_template_string(HTML, error=error)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

