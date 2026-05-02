from PySide6.QtWidgets import QMessageBox, QColorDialog, QFileDialog, QApplication
from PySide6.QtGui import QColor

"""
Unified Dialogs Module.
Provides native PySide6 implementations for common dialog types, 
maintaining a consistent API across the application.
"""

def _get_parent():
    """Attempts to find the active main window so dialogs do not open without a parent."""
    app = QApplication.instance()
    if app:
        return app.activeWindow()
    return None

def showinfo(title, message):
    QMessageBox.information(_get_parent(), title, str(message))

def showerror(title, message):
    QMessageBox.critical(_get_parent(), title, str(message))

def askyesno(title, message):
    reply = QMessageBox.question(
        _get_parent(), title, str(message), 
        QMessageBox.Yes | QMessageBox.No
    )
    return reply == QMessageBox.Yes

def askcolor(initialcolor=None, title="Choose Colour"):
    """
    Standard colour selection dialog.
    Uses a neutral Qt dialog (to avoid CSS inheritance) with manual icon and centering.
    Returns a tuple ((R, G, B), '#hex') to ensure compatibility with backend logic.
    """
    initial = QColor(initialcolor) if initialcolor else QColor()
    parent = _get_parent()
    
    # We use parent=None to prevent the dialog from inheriting the global blue stylesheet,
    # which ensures it looks 'clean' and correctly formatted.
    dialog = QColorDialog(initial) 
    dialog.setWindowTitle(title)
    dialog.setOption(QColorDialog.DontUseNativeDialog)
    
    # Manually apply the application icon
    if parent:
        dialog.setWindowIcon(parent.windowIcon())
        
        # Manually center the dialog over the main window
        dialog.show() # Brief show to calculate size
        geo = dialog.geometry()
        p_geo = parent.geometry()
        x = p_geo.x() + (p_geo.width() - geo.width()) // 2
        y = p_geo.y() + (p_geo.height() - geo.height()) // 2
        dialog.move(x, y)
        dialog.hide()
    
    if dialog.exec() == QColorDialog.Accepted:
        color = dialog.currentColor()
        return ((color.red(), color.green(), color.blue()), color.name())
    return None, None

def asksaveasfilename(**kwargs):
    """
    Standard file saving dialog.
    Translates filter formats to native Qt formats.
    """
    parent = _get_parent()
    title = kwargs.get('title', 'Save As')
    initialdir = kwargs.get('initialdir', '')
    initialfile = kwargs.get('initialfile', '')
    
    # Convert filetypes from [("Name", "*.ext")] to "Name (*.ext);;Name2 (*.ext2)"
    filetypes = kwargs.get('filetypes', [])
    filter_str = ";;".join([f"{name} ({ext})" for name, ext in filetypes])
    
    # Build initial path
    import os
    initial_path = os.path.join(initialdir, initialfile) if initialdir else initialfile
    
    path, _ = QFileDialog.getSaveFileName(parent, title, initial_path, filter_str)
    return path
