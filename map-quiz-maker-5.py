import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk
import math

class ImageClickApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Map Quiz Maker")

        self.img_width = 0
        self.img_height = 0
        self.scale_factor = 1
        self.quiz_locations = []
        self.label_radius = 10
        self.next_number = 1

        # Create a button to load the image
        load_button = tk.Button(root, text="Load Image", command=self.load_image)
        load_button.pack(pady=10)

        # Create a frame to hold the canvas and scrollbars
        self.frame = ttk.Frame(root)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Create a canvas for the image
        self.canvas = tk.Canvas(self.frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add vertical scrollbar
        self.v_scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add horizontal scrollbar
        self.h_scrollbar = ttk.Scrollbar(root, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar.pack(fill=tk.X)

        # Configure the canvas
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        # Create a label to display results
        self.result_label = tk.Label(root, text="Load an image to begin", pady=10)
        self.result_label.pack()

        # Bind the click event to the canvas
        self.canvas.bind("<Button-1>", self.on_canvas_click)

    def on_canvas_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_click(self, event):
        if self.img_width == 0 or self.img_height == 0:
            return  # No image loaded

        # Get the current scroll position
        x_scroll = self.canvas.canvasx(event.x)
        y_scroll = self.canvas.canvasy(event.y)

        # Calculate the percentage for x and y, accounting for scaling and scrolling
        x_percentage = x_scroll / (self.img_width * self.scale_factor)
        y_percentage = 1 - (y_scroll / (self.img_height * self.scale_factor))  # Invert y-axis
        
        x_location = round(x_percentage * self.img_width_cm, 1)
        y_location = round(y_percentage * self.img_height_cm, 1)
        
        self.result_label.config(text=f"Clicked at: ({x_location:.1f} cm, {y_location:.1f} cm)")

        # Check if we clicked on an existing label
        clicked_items = self.canvas.find_overlapping(x_scroll-5, y_scroll-5, x_scroll+5, y_scroll+5)
        for item in clicked_items:
            if self.canvas.type(item) == "text":
                # Remove the label
                number = int(self.canvas.itemcget(item, 'text'))
                self.canvas.delete(item)
                
                # Remove the corresponding location
                self.quiz_locations = [loc for loc in self.quiz_locations if loc[2] != number]
                print(f"Removed location number {number}")
                return

        # If we didn't click on an existing label, add a new one
        self.add_new_label(x_scroll, y_scroll, x_location, y_location)

        print("Current quiz locations:", self.quiz_locations)

    def add_new_label(self, x_scroll, y_scroll, x_location, y_location):
        label = self.canvas.create_text(
            x_scroll, y_scroll,
            text=str(self.next_number),
            fill="red",
            font=("Arial", 12, "bold")
        )
        self.quiz_locations.append((x_location, y_location, self.next_number))
        print(f"Added new location {self.next_number}: ({x_location:.1f}, {y_location:.1f})")
        self.next_number += 1

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif")])
        if file_path:
            image = Image.open(file_path)
            self.img_width, self.img_height = image.size
            self.img_width_cm = 17.78  # 17.78 is \textwidth in LaTeX worksheet (i.e. 7")
            self.img_height_cm = self.img_width_cm * self.img_height / self.img_width

            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth() * 0.8  # Use 80% of screen width
            screen_height = self.root.winfo_screenheight() * 0.8  # Use 80% of screen height

            # Calculate scaling factor
            width_ratio = screen_width / self.img_width
            height_ratio = screen_height / self.img_height
            self.scale_factor = min(width_ratio, height_ratio, 1)  # Don't scale up, only down

            # Scale the image
            new_width = int(self.img_width * self.scale_factor)
            new_height = int(self.img_height * self.scale_factor)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            photo = ImageTk.PhotoImage(image)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            self.canvas.image = photo  # Keep a reference

            # Update canvas scroll region
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

            self.result_label.config(text="Click on the image to add or remove quiz locations")
            self.quiz_locations = []  # Reset quiz locations when loading a new image
            self.next_number = 1  # Reset the numbering when loading a new image

# Create the main window and start the app
root = tk.Tk()
app = ImageClickApp(root)
root.mainloop()