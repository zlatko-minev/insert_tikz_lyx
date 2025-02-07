## **LyX TikZ Figure Numbering Script**

### **What is this?**
This script processes a **LyX document** to identify and number **ERT (Evil Red Text) blocks**, which embed **LaTeX code**. It specifically looks for **TikZ graphics** and ensures each figure has a **unique `tikzsetname`**.

### **Why is this needed?**
When using **externalization in TikZ**, every figure must have a unique name to avoid conflicts during compilation. This script automates the process by:
- **Scanning** all ERT blocks for existing `tikzsetname` definitions.
- **Finding the highest existing number** used.
- **Assigning sequential numbers** to any missing or unnamed `tikzsetname` entries.
- **Providing detailed debug output** to track modifications.

### **Small issues**
The script correctly assigns numbers to new TikZ figures but **fails to identify some pre-existing `tikzsetname` values**. This could result in **duplicate or incorrect numbering**. The script likely needs **a more robust detection mechanism** for `tikzsetname` within **ERT blocks**, ensuring it properly captures all pre-existing names before assigning new ones.
