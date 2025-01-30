import tkinter as tk
from tkinter import filedialog, ttk
from tkinter import simpledialog
from PIL import Image, ImageTk
import os
import random
import re
import shutil

class ImageClickApp:
    def __init__(self, root):
        # Existing initialization code...
        
        # Add Save and Load buttons
        save_button = tk.Button(self.right_frame, text="Save State", command=self.save_state)
        save_button.grid(row=7, column=0, pady=5)
        
        load_button = tk.Button(self.right_frame, text="Load State", command=self.load_state)
        load_button.grid(row=8, column=0, pady=5)
    
    def save_state(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not save_path:
            return
        
        state = {
            "image_file_path": self.image_file_path,
            "quiz_locations": self.quiz_locations,
            "class": self.class_entry.get(),
            "title": self.title_entry.get(),
            "version": self.version_entry.get(),
            "instructions": self.instructions_entry.get()
        }
        
        with open(save_path, 'w') as file:
            json.dump(state, file, indent=4)
        print(f"State saved to {save_path}")
    
    def load_state(self):
        load_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not load_path:
            return
        
        with open(load_path, 'r') as file:
            state = json.load(file)
        
        self.image_file_path = state.get("image_file_path")
        self.quiz_locations = state.get("quiz_locations", [])
        
        self.class_entry.delete(0, tk.END)
        self.class_entry.insert(0, state.get("class", ""))
        
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, state.get("title", ""))
        
        self.version_entry.delete(0, tk.END)
        self.version_entry.insert(0, state.get("version", ""))
        
        self.instructions_entry.delete(0, tk.END)
        self.instructions_entry.insert(0, state.get("instructions", ""))
        
        if self.image_file_path:
            self.load_image()  # Reload image
        
        self.update_answer_list()
        print(f"State loaded from {load_path}")


    def create_label_entry(self, parent, label_text, row):
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky='w', padx=5)
        entry = ttk.Entry(parent)
        entry.grid(row=row, column=0, sticky='e', padx=5, pady=2)
        return entry

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
        self.canvas.create_text(
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

        # Configure answer_list_frame to expand horizontally
        self.answer_list_frame.columnconfigure(0, weight=1)

        # Populate the answer list with the current quiz locations
        for idx, (number, x, y, answer) in enumerate(self.quiz_locations):
            frame = ttk.Frame(self.answer_list_frame)
            frame.grid(row=idx, column=0, sticky='ew', padx=5, pady=2)

            # Configure the frame to expand horizontally
            frame.columnconfigure(0, weight=0)  # Label column (fixed size)
            frame.columnconfigure(1, weight=1)  # Entry column (expandable)

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
            self.img_width_cm = 17.78  # 17.78 is \textwidth in LaTeX worksheet (i.e., 7")
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
            self.image_file_path = file_path
            self.quiz_locations = []  # Reset quiz locations when loading a new image
            self.next_number = 1  # Reset numbering when loading a new image
            self.update_answer_list()  # Clear the answer list



    def build_quiz(self):
        if not self.image_file_path:
            print("No image loaded!")
            return

        # Ensure output directory exists
        output_dir = 'tex_output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Extract the image filename
        image_filename = os.path.basename(self.image_file_path)
        image_output_path = os.path.join(output_dir, image_filename)

        # Copy image to tex_output if it doesn't already exist
        if not os.path.exists(image_output_path):
            shutil.copy(self.image_file_path, image_output_path)
            print(f"Image copied to {image_output_path}")

        # Update the LaTeX to point to the copied image
        latex_image_path = image_filename  # LaTeX should refer to just the filename

        # Randomize the order of quiz locations
        random.shuffle(self.quiz_locations)

        # Create TikZ nodes for the labels
        nodes_and_labels = "\n".join(
            f"\\node at ({x}, {y}) {{\\textbf{{{index + 1}}}}};"
            for index, (number, x, y, _) in enumerate(self.quiz_locations)
        )

        # Create questions and answers
        questions_and_answers = "\n".join(
            f"\\question\\MatchQuestion{{{answer}}}{{}} \\vfill"
            for _, _, _, answer in self.quiz_locations
        )

        # Create answers for the second page key
        answers_for_key = "\n".join(
            f"\\item {answer}"
            for _, _, _, answer in self.quiz_locations
        )

        # Read template
        template_path = os.path.join(os.path.dirname(__file__), 'Image_Overlay_Worksheet_Template.tex')
        with open(template_path, 'r') as template_file:
            template_content = template_file.read()

        # Replace placeholders in the template
        template_content = template_content.replace(
            "!CLASS!", self.class_entry.get()).replace(
            "!TITLE!", self.title_entry.get()).replace(
            "!VERSION!", self.version_entry.get()).replace(
            "!INSTRUCTIONS!", self.instructions_entry.get()).replace(
            "!IMAGE_FILE!", latex_image_path).replace(
            "!NODES_AND_LABELS!", nodes_and_labels).replace(
            "!QUESTIONS_AND_ANSWERS!", questions_and_answers).replace(
            "!ANSWERS_FOR_KEY!", answers_for_key)
        
        template_content_answers = template_content.replace('%answers,', 'answers,')

        # Make output filename
        output_filename = f"{self.class_entry.get()}_{self.title_entry.get()}_{self.version_entry.get()}"
        output_filename = re.sub("\s", "_", output_filename)

        # Write to output file
        output_path = os.path.join(output_dir, output_filename + ".tex")
        with open(output_path, 'w') as output_file:
            output_file.write(template_content)

        # All the below commented-out code was to save a second copy that would be an
        # answer key. But I think I would rather have a second page of the document be 
        # an attached answer key. Not 100% sure, though, hence the mere commenting out.

        # Write to answer file
        #output_path_answers = os.path.join(output_dir, output_filename + "_ANSWERS.tex")
        #with open(output_path_answers, 'w') as output_file:
        #    output_file.write(template_content_answers)

        #print(f"Quiz saved to {output_path} and {output_path_answers}")
        print(f"Quiz saved to {output_path}.")


# Create the main window and start the app
root = tk.Tk()
app = ImageClickApp(root)
root.mainloop()