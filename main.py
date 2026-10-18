import os
import struct
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import zlib
from PIL import Image, ImageTk

# Format Specifications
MAGIC_HEADER = b"HUFI"
HEADER_FORMAT = "<4sIIB"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# Pillow compatibility helper for resampling
RESAMPLE_FILTER = getattr(Image, "Resampling", Image).LANCZOS


def get_resource_path(relative_path: str) -> str:
    """Returns the absolute path to a resource, working for both dev scripts and PyInstaller bundles."""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller extracts bundled files to a temporary folder (_MEIPASS)
        return os.path.join(sys._MEIPASS, relative_path)
    # Standard script execution: locate file relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, relative_path)


def undo_sub_filter(width: int, height: int, filtered_bytes: bytes) -> bytes:
    """Reconstructs raw RGB pixels from left-neighbor deltas in memory."""
    raw = bytearray()
    for y in range(height):
        row_start = y * width * 3
        for x in range(width):
            i = row_start + x * 3
            if x == 0:
                raw.extend(filtered_bytes[i : i + 3])
            else:
                prev_i = row_start + (x - 1) * 3
                r = (filtered_bytes[i] + raw[prev_i]) & 0xFF
                g = (filtered_bytes[i + 1] + raw[prev_i + 1]) & 0xFF
                b = (filtered_bytes[i + 2] + raw[prev_i + 2]) & 0xFF
                raw.extend([r, g, b])
    return bytes(raw)


def load_hufi_to_pil(filename: str) -> tuple[Image.Image, int, int]:
    """Reads a .hufi file and converts it directly into an in-memory PIL Image."""
    with open(filename, "rb") as f:
        header_data = f.read(HEADER_SIZE)
        if len(header_data) < HEADER_SIZE:
            raise ValueError(
                "File is too small to contain a valid .hufi header."
            )

        magic, width, height, channels = struct.unpack(
            HEADER_FORMAT, header_data
        )

        if magic != MAGIC_HEADER:
            raise ValueError(
                f"Invalid format signature: expected {MAGIC_HEADER}, got {magic}"
            )

        compressed_payload = f.read()
        filtered_data = zlib.decompress(compressed_payload)
        raw_rgb = undo_sub_filter(width, height, filtered_data)

        pil_img = Image.frombytes("RGB", (width, height), raw_rgb)
        return pil_img, width, height


class HufiViewerApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("HUFI Viewer")

        # --- Dynamic Icon Path Resolution ---
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        self.root.geometry("800x600")
        self.root.configure(bg="#1e1e1e")

        # Image state variables
        self.pil_img = None
        self.tk_img = None
        self.zoom_factor = 1.0
        self.current_filename = ""

        # --- Build Menu Bar ---
        self.menu_bar = tk.Menu(self.root)

        # File Menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(
            label="Open Image...", command=self.open_file, accelerator="Ctrl+O"
        )
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.quit)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

        # View Menu
        self.view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.view_menu.add_command(
            label="Zoom In", command=self.zoom_in, accelerator="Ctrl++"
        )
        self.view_menu.add_command(
            label="Zoom Out", command=self.zoom_out, accelerator="Ctrl+-"
        )
        self.view_menu.add_command(
            label="Reset Zoom (100%)",
            command=self.reset_zoom,
            accelerator="Ctrl+0",
        )
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)

        # Help Menu
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(
            label="Documentation", command=self.show_documentation
        )
        self.help_menu.add_command(label="License", command=self.show_license)
        self.help_menu.add_separator()
        self.help_menu.add_command(
            label="About HUFI Viewer", command=self.show_about
        )
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)

        self.root.config(menu=self.menu_bar)

        # --- Canvas Display ---
        self.canvas = tk.Canvas(self.root, bg="#111111", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # --- Status Bar ---
        self.status_bar = tk.Label(
            self.root,
            text="No image loaded. Use File -> Open to load a .hufi file.",
            bg="#252526",
            fg="#cccccc",
            anchor="w",
            padx=10,
            pady=3,
            font=("Arial", 9),
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # --- Key & Mouse Bindings ---
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-KP_Add>", lambda e: self.zoom_in())  # Numpad +
        self.root.bind(
            "<Control-equal>", lambda e: self.zoom_in()
        )  # Ctrl+= (standard keyboard +)
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind(
            "<Control-KP_Subtract>", lambda e: self.zoom_out()
        )  # Numpad -
        self.root.bind("<Control-0>", lambda e: self.reset_zoom())

        # Mouse Wheel Zoom
        self.root.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows / macOS
        self.root.bind("<Button-4>", lambda e: self.zoom_in())  # Linux Scroll Up
        self.root.bind(
            "<Button-5>", lambda e: self.zoom_out()
        )  # Linux Scroll Down

        # Click-and-Drag Panning
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.pan)

        if len(sys.argv) > 1:
            file_path = sys.argv[1]
            # Schedule file loading right after the Tkinter window initializes
            self.root.after(100, lambda: self.load_image_from_path(file_path))

    def load_image_from_path(self, filepath: str):
        try:
            self.pil_img, w, h = load_hufi_to_pil(filepath)
            self.current_filename = filepath.split("/")[-1].split("\\")[-1]
            self.zoom_factor = 1.0
            self.render_image()
            self.root.title(f".HUFI Viewer - {self.current_filename}")
        except Exception as e:
            messagebox.showerror("Error Opening File", str(e))

    def open_file(self):
        filepath = filedialog.askopenfilename(
            title="Open HUFI Image",
            filetypes=[("HUFI Image Files", "*.hufi"), ("All Files", "*.*")],
        )
        if filepath:
            try:
                self.pil_img, w, h = load_hufi_to_pil(filepath)
                self.current_filename = filepath.split("/")[-1]
                self.zoom_factor = 1.0
                self.render_image()
                self.root.title(f"HUFI Viewer - {self.current_filename}")
            except Exception as e:
                messagebox.showerror("Error Opening File", str(e))

    def render_image(self):
        if not self.pil_img:
            return

        orig_w, orig_h = self.pil_img.size
        new_w = max(1, int(orig_w * self.zoom_factor))
        new_h = max(1, int(orig_h * self.zoom_factor))

        # Scale image buffer in memory
        resized = self.pil_img.resize((new_w, new_h), RESAMPLE_FILTER)
        self.tk_img = ImageTk.PhotoImage(resized)

        # Clear and redraw canvas image centered
        self.canvas.delete("all")
        cx = self.canvas.winfo_width() // 2 or 400
        cy = self.canvas.winfo_height() // 2 or 300

        self.canvas.create_image(cx, cy, image=self.tk_img, anchor=tk.CENTER)

        # Update status bar metadata
        zoom_pct = int(self.zoom_factor * 100)
        self.status_bar.config(
            text=f"File: {self.current_filename} | Resolution: {orig_w}x{orig_h} px | Zoom: {zoom_pct}%"
        )

    def zoom_in(self):
        if self.pil_img and self.zoom_factor < 10.0:
            self.zoom_factor *= 1.25
            self.render_image()

    def zoom_out(self):
        if self.pil_img and self.zoom_factor > 0.05:
            self.zoom_factor /= 1.25
            self.render_image()

    def reset_zoom(self):
        if self.pil_img:
            self.zoom_factor = 1.0
            self.render_image()

    def on_mouse_wheel(self, event):
        if not self.pil_img:
            return
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def pan(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def show_about(self):
        messagebox.showinfo(
            "About HUFI Viewer",
            "Hagan's Ultimate Format for Images (HUFI) Viewer v1.0.0\n\nA lightweight viewer for .hufi image files.\n\nDeveloped by Hagan Ernest Pereira.",
        )

    def show_documentation(self):
        messagebox.showinfo(
            "Documentation",
            """
Basic Usage:-

Open File: Click File --> Open Image... or press Ctrl + O. Select any .hufi file.
Zoom: Scroll the Mouse Wheel up/down, or use View menu commands.
Pan: Click and drag with the Left Mouse Button to move around a zoomed image.
Status Bar: Check the bar at the bottom for image resolution, file name, and zoom level.

Shortcuts:-

Action --> Shortcut
Open Image --> Ctrl + O
Zoom In --> Ctrl + + / Mouse Wheel Up
Zoom Out --> Ctrl + - / Mouse Wheel Down
Reset Zoom (100%) --> Ctrl + 0
Pan / Drag --> Left-Click + Drag
""",
        )

    def show_license(self):
        messagebox.showinfo(
            "License",
            """Copyright 2026 Hagan Ernest Pereira

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.""",
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = HufiViewerApp(root)
    root.mainloop()