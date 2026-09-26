# Evidencias de la versión ampliada

- 65 pruebas aprobadas en Windows / Python 3.12.14.
- Cobertura de líneas y ramas del backend: 99,47 %. `donations.py` y `validation.py`: 100 % en esta ejecución.
- Salida real: `pytest.txt`; JUnit: `resultados.xml`; reporte navegable: `cobertura/index.html`.
- Flujo de interfaz comprobado con Microsoft Edge y Playwright. Resultado en `prueba-navegador.json`.
- Capturas reales del login, destinos, registro de donación, seguimiento, resumen, historial y vista móvil.
- Las organizaciones y donaciones de las capturas son ficticias y se crearon en una base de prueba separada. No se insertaron en la base del usuario.

Docker, GitHub Actions, ZAP y SonarQube no se ejecutaron aquí. Sus configuraciones están incluidas y deben verificarse en los entornos correspondientes. No se considera la prueba local como un despliegue público.
