import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def create_flowchart():
    # Set up the figure
    fig, ax = plt.subplots(figsize=(10, 14))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 24)
    ax.axis('off')
    
    # Define box dimensions
    box_width = 6
    box_height = 1
    x_center = 5
    
    # Define new colors and styles
    box_color = '#1abc9c'  # Teal
    arrow_color = '#34495e'  # Dark gray
    text_color = 'white'
    font = {'fontname': 'Arial', 'fontsize': 10, 'fontweight': 'bold'}
    
    # Define positions (from bottom to top)
    positions = {
        'End': 1,
        'Real-time Video Feed Handling': 3,
        'Adaptive Update': 5,
        'Performance Opt': 7,
        'Database Access': 9,
        'Tolerance Set': 11,
        'Face Comparison': 13,
        'Data Compression': 15,
        'Face Encoding': 17,
        'CNN-based Detection': 19,
        'Detection Failed?': 20.5,
        'Face Detection': 22,
        'Start': 23
    }
    
    # Helper function to create boxes with rounded corners
    def add_box(label, y_pos, special_width=None):
        width = special_width if special_width else box_width
        x = x_center - width/2
        rect = patches.FancyBboxPatch((x, y_pos), width, box_height, 
                                      boxstyle="round,pad=0.1", 
                                      linewidth=1, edgecolor='black', 
                                      facecolor=box_color, alpha=0.9)
        ax.add_patch(rect)
        ax.text(x_center, y_pos + box_height/2, label, 
                horizontalalignment='center', 
                verticalalignment='center',
                color=text_color, **font)
    
    # Add all boxes
    for label, y_pos in positions.items():
        if label == 'Detection Failed?':
            add_box(label, y_pos, 4)  # Smaller width for decision box
        else:
            add_box(label, y_pos)
    
    # Add detailed labels to certain boxes
    details = {
        'Face Detection': '(HOG-based)',
        'Face Encoding': '(128-D Feature)',
        'Face Comparison': '(Euclidean Dist.)',
        'Performance Opt': '(Frame Sampling, Caching, Parallel Processing)',
        'Adaptive Update': '(Lighting Adj.)'
    }
    
    for box, detail in details.items():
        y_pos = positions[box]
        ax.text(x_center, y_pos + box_height/2 - 0.3, detail, 
                horizontalalignment='center', 
                verticalalignment='center', 
                color=text_color, fontsize=8)
    
    # Add vertical arrows with thicker lines
    for i, label in enumerate(list(positions.keys())[:-1]):
        next_label = list(positions.keys())[i+1]
        y_start = positions[label] + box_height
        y_end = positions[next_label]
        
        # Skip the arrow from Detection Failed to CNN-based Detection
        if label == 'Detection Failed?' and next_label == 'CNN-based Detection':
            continue
            
        # Draw vertical arrow
        ax.arrow(x_center, y_start, 0, y_end - y_start - 0.1, 
                head_width=0.3, head_length=0.2, fc=arrow_color, ec=arrow_color, linewidth=2)
    
    # Add special arrows for decision box (Detection Failed?)
    # No arrow (left)
    y_decision = positions['Detection Failed?']
    ax.arrow(x_center - 1, y_decision + box_height/2, 0, -1.9, 
            head_width=0.3, head_length=0.2, fc=arrow_color, ec=arrow_color, linewidth=2)
    ax.text(x_center - 1.3, y_decision + box_height/2 - 1, 'No', 
            horizontalalignment='right', color='black', fontweight='bold')
    
    # Yes arrow (right)
    ax.arrow(x_center + 1, y_decision + box_height/2, 0, -1.9, 
            head_width=0.3, head_length=0.2, fc=arrow_color, ec=arrow_color, linewidth=2)
    ax.text(x_center + 1.3, y_decision + box_height/2 - 1, 'Yes', 
            horizontalalignment='left', color='black', fontweight='bold')
    
    # Title
    plt.title('Face Recognition System Flow', fontsize=16, pad=20, fontweight='bold')
    
    # Save the figure
    plt.tight_layout()
    plt.savefig('docs/face_recognition_flowchart.png', dpi=300, bbox_inches='tight')
    plt.savefig('docs/face_recognition_flowchart.svg', format='svg', bbox_inches='tight')
    
    print("Flowchart created successfully and saved as 'docs/face_recognition_flowchart.png' and 'docs/face_recognition_flowchart.svg'")

if __name__ == "__main__":
    create_flowchart()
