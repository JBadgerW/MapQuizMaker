import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk

class ImageClickApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Map Quiz Maker")

        self.img_width = 0
        self.img_height = 0
        self.scale_factor = 1
        self.quiz_locations = []
        self.next_number = 1

        # Create a main frame to hold everything
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create a frame for the left side (image and controls)
        self.left_frame = ttk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create a button to load the image
        load_button = tk.Button(self.left_frame, text="Load Image", command=self.load_image)
        load_button.pack(pady=10)

        # Create a frame to hold the canvas and scrollbars
        self.canvas_frame = ttk.Frame(self.left_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Create a canvas for the image
        self.canvas = tk.Canvas(self.canvas_frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add vertical scrollbar for the canvas
        self.v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add horizontal scrollbar for the canvas
        self.h_scrollbar = ttk.Scrollbar(self.left_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.h_scrollbar.pack(fill=tk.X)

        # Configure the canvas
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        # Create a label to display results
        self.result_label = tk.Label(self.left_frame, text="Load an image to begin", pady=10)
        self.result_label.pack()

        # Bind the click event to the canvas
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # Create a frame for the right side (answer list) with fixed width
        self.right_frame = ttk.Frame(self.main_frame, width=380)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.right_frame.pack_propagate(False)  # Prevent the frame from shrinking

        # Create a label for the answer list
        answer_label = tk.Label(self.right_frame, text="Answers", font=("Arial", 14, "bold"))
        answer_label.pack(pady=10)

        # Create a canvas for the answer list
        self.answer_canvas = tk.Canvas(self.right_frame)
        self.answer_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add a scrollbar for the answer list
        self.answer_scrollbar = ttk.Scrollbar(self.right_frame, orient=tk.VERTICAL, command=self.answer_canvas.yview)
        self.answer_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure the answer canvas
        self.answer_canvas.configure(yscrollcommand=self.answer_scrollbar.set)
        self.answer_canvas.bind('<Configure>', self.on_answer_canvas_configure)

        # Create a frame inside the canvas to hold the answer list items
        self.answer_list_frame = ttk.Frame(self.answer_canvas)
        self.answer_list_window = self.answer_canvas.create_window((0, 0), window=self.answer_list_frame, anchor=tk.NW)

        # Bind the answer list frame to update scroll region
        self.answer_list_frame.bind('<Configure>', self.on_answer_frame_configure)

    def on_canvas_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_answer_canvas_configure(self, event):
        self.answer_canvas.itemconfig(self.answer_list_window, width=event.width)

    def on_answer_frame_configure(self, event):
        self.answer_canvas.configure(scrollregion=self.answer_canvas.bbox("all"))

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
                number = self.canvas.itemcget(item, 'text')
                self.canvas.delete(item)
                
                # Remove the corresponding location and answer entry
                self.quiz_locations = [loc for loc in self.quiz_locations if loc[0] != number]
                self.update_answer_list()
                print(f"Removed location number {number}")
                return

        # If we didn't click on an existing label, add a new one
        self.add_new_label(x_scroll, y_scroll, x_location, y_location)

        print("Current quiz locations:", self.quiz_locations)

    def add_new_label(self, x_scroll, y_scroll, x_location, y_location):
        label_text = str(self.next_number)
        label = self.canvas.create_text(
            x_scroll, y_scroll,
            text=label_text,
            fill="red",
            font=("Arial", 12, "bold")
        )
        self.quiz_locations.append((label_text, x_location, y_location, ""))  # Empty string for answer
        print(f"Added new location {label_text}: ({x_location:.1f}, {y_location:.1f})")
        self.next_number += 1
        self.update_answer_list()

    def update_answer_list(self):
        # Clear the existing answer list
        for widget in self.answer_list_frame.winfo_children():
            widget.destroy()

        # Populate the answer list with the current quiz locations
        for number, x, y, answer in self.quiz_locations:
            frame = ttk.Frame(self.answer_list_frame)
            frame.pack(fill=tk.X, padx=5, pady=2)
            frame.columnconfigure(1, weight=1)  # Make the second column (entry) expandable

            label = ttk.Label(frame, text=f"{number}:", width=5)
            label.grid(row=0, column=0, sticky="w")

            entry = ttk.Entry(frame)
            entry.grid(row=0, column=1, sticky="ew")
            entry.insert(0, answer)
            entry.bind('<FocusOut>', lambda e, num=number: self.update_answer(num, e.widget.get()))

        # Update the answer canvas scroll region
        self.answer_list_frame.update_idletasks()
        self.answer_canvas.configure(scrollregion=self.answer_canvas.bbox("all"))

    def update_answer(self, number, new_answer):
        for i, (num, x, y, _) in enumerate(self.quiz_locations):
            if num == number:
                self.quiz_locations[i] = (num, x, y, new_answer)
                break
        print(f"Updated answer for number {number}: {new_answer}")

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif")])
        if file_path:
            image = Image.open(file_path)
            self.img_width, self.img_height = image.size
            self.img_width_cm = 17.78  # 17.78 is \textwidth in LaTeX worksheet (i.e. 7")
            self.img_height_cm = self.img_width_cm * self.img_height / self.img_width

            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth() - 380  # Subtract answer list width
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
            self.update_answer_list()  # Clear the answer list

# Create the main window and start the app
root = tk.Tk()
app = ImageClickApp(root)
root.mainloop()
