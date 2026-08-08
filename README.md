# Dashboard Cencosud vs Falabella

Dashboard interactivo en Streamlit que compara la acción de **Cencosud** (`CENCOSUD.SN`) con **Falabella** (`FALABELLA.SN`) usando datos de Yahoo Finance.

## Ejecutar localmente

```bash
source .venv/bin/activate
streamlit run app.py
```

## Vistas disponibles

- Precio ajustado
- Relación Precio/Utilidad (P/E)
- Capitalización de mercado
- Utilidad neta
- Margen de utilidad neta
- Dividendo yield

## Stack

- Streamlit
- Plotly
- yfinance
- pandas
