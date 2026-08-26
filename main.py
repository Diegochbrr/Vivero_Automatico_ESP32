import sys
from PyQt6.QtWidgets import QApplication
from modelo import ModeloRiego
from vista import VistaRiego
from controlador import ControladorRiego

def main():
    app = QApplication(sys.argv)
    
    modelo = ModeloRiego()
    vista = VistaRiego()
    controlador = ControladorRiego(vista, modelo)
    
    vista.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()