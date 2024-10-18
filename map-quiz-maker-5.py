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
        self.dot_radius = 5

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

        # Check if we clicked on an existing dot
        clicked_item = self.canvas.find_closest(x_scroll, y_scroll)
        if clicked_item and self.canvas.type(clicked_item[0]) == "oval":
            # Check if the click is within the dot
            dot_coords = self.canvas.coords(clicked_item[0])
            dot_center_x = (dot_coords[0] + dot_coords[2]) / 2
            dot_center_y = (dot_coords[1] + dot_coords[3]) / 2
            distance = math.sqrt((x_scroll - dot_center_x)**2 + (y_scroll - dot_center_y)**2)
            
            if distance <= self.dot_radius:
                # Remove the dot
                self.canvas.delete(clicked_item[0])
                
                # Find and remove the corresponding location
                closest_location = min(self.quiz_locations, 
                                       key=lambda loc: abs(loc[0] - x_location) + abs(loc[1] - y_location))
                self.quiz_locations.remove(closest_location)
                print(f"Removed location: {closest_location}")
            else:
                # Click was not close enough to the dot center, treat as a new dot
                self.add_new_dot(x_scroll, y_scroll, x_location, y_location)
        else:
            # Add a new dot and location
            self.add_new_dot(x_scroll, y_scroll, x_location, y_location)

        print("Current quiz locations:", self.quiz_locations)

    def add_new_dot(self, x_scroll, y_scroll, x_location, y_location):
        dot = self.canvas.create_oval(
            x_scroll - self.dot_radius, y_scroll - self.dot_radius,
            x_scroll + self.dot_radius, y_scroll + self.dot_radius,
            fill="red", outline="red"
        )
        self.quiz_locations.append((x_location, y_location))
        print(f"Added new location: ({x_location:.1f}, {y_location:.1f})")

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

# Create the main window and start the app
root = tk.Tk()
app = ImageClickApp(root)
root.mainloop()