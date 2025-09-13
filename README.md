<p align="center">
  <img src="docs/branding/blockshelf-logo.png" alt="BlockShelf" width="260" />
</p>

<h1 align="center">BlockShelf</h1>

<p align="center">
  A clean, local‑first LEGO® parts inventory app — import, search, share, and collaborate.
</p>

---

## ✨ Highlights

- 🔎 <strong>Clean inventory UI</strong> with search, sort, pagination & dark mode
- 📥 <strong>Import</strong> CSV/XLS/XLSX (and export CSV)
- 🧠 <strong>Local‑first part lookups</strong> with Rebrickable API fallback
- 🧩 <strong>Rebrickable Bootstrap</strong>: seed local data from downloads ZIP (<code>colors.csv</code>, <code>parts.csv</code>, <code>elements.csv</code>)
- 🔗 <strong>Share &amp; collaborate</strong>: public links and invitations with permissions

> LEGO® is a trademark of the LEGO Group, which does not sponsor, authorize or endorse this project.

---

## 🚀 Quick Start (Local)

```bash
git clone https://github.com/DarkSmileee/BlockShelf.git
cd BlockShelf

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -U pip
pip install -r requirements.txt

cp .env.example .env
python manage.py migrate
python manage.py createcachetable
python manage.py runserver
```

Optional: create an admin user

```bash
python manage.py createsuperuser
```

---

## 📸 Screenshots

### Dark
<p>
  <img src="docs/printscreens/dark/dark_inventory.png" width="420" alt="Inventory (Dark)">
  <img src="docs/printscreens/dark/dark_add_item.png" width="420" alt="Add Item (Dark)">
</p>
<p>
  <img src="docs/printscreens/dark/dark_login.png" width="420" alt="Login (Dark)">
  <img src="docs/printscreens/dark/dark_settings.png" width="420" alt="Settings (Dark)">
</p>

### Light
<p>
  <img src="docs/printscreens/light/light_inventory.png" width="420" alt="Inventory (Light)">
  <img src="docs/printscreens/light/light_add_item.png" width="420" alt="Add Item (Light)">
</p>
<p>
  <img src="docs/printscreens/light/light_login.png" width="420" alt="Login (Light)">
  <img src="docs/printscreens/light/light_settings.png" width="420" alt="Settings (Light)">
</p>

---

## 📄 License

Released under the <strong>PolyForm Noncommercial License 1.0.0</strong> — see <a href="LICENSE">LICENSE</a>.
