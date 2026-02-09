import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib import colors

# Define el directorio absoluto donde se guardarán los recibos
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DIRECTORIO_RECIBOS = os.path.join(PROJECT_ROOT, "output", "recibos")

def crear_recibo(nombre_restaurante, items_carrito, total_str):
    """
    Función original mantenida para compatibilidad.
    Crea un archivo PDF con los detalles de la compra.
    """
    return crear_recibo_simple(nombre_restaurante, items_carrito, total_str)

def crear_recibo_simple(nombre_restaurante, items_carrito, total_str, folio_numero=None):
    """
    Crea un recibo PDF simple (sin secciones) - mantiene compatibilidad.
    """
    try:
        # 1. Crear el directorio 'recibos' si no existe
        os.makedirs(DIRECTORIO_RECIBOS, exist_ok=True)

        # 2. Generar un nombre de archivo único
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folio_suffix = f"_Folio_{folio_numero}" if folio_numero else ""
        nombre_archivo = f"Recibo_{nombre_restaurante.replace(' ', '_')}_{timestamp}{folio_suffix}.pdf"
        ruta_archivo = os.path.join(DIRECTORIO_RECIBOS, nombre_archivo)

        # 3. Configurar el documento PDF
        doc = SimpleDocTemplate(ruta_archivo, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # 4. Construir el contenido del PDF
        # Header con título y folio
        if folio_numero:
            # Crear tabla para header con folio en esquina superior derecha
            header_data = [["Bodega de Insumos 'Disfruleg'", f"FOLIO: {folio_numero:06d}"]]
            header_table = Table(header_data, colWidths=[400, 150])
            header_style = TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (0, 0), 18),
                ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (1, 0), (1, 0), 14),
                ('TEXTCOLOR', (1, 0), (1, 0), colors.red),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ])
            header_table.setStyle(header_style)
            story.append(header_table)
        else:
            # Título principal sin folio
            story.append(Paragraph("Bodega de Insumos 'Disfruleg'", styles['h1']))
        
        story.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
        story.append(Spacer(1, 24))

        # Información del cliente
        story.append(Paragraph(f"<b>Recibo para:</b> {nombre_restaurante}", styles['h2']))
        story.append(Spacer(1, 12))

        # Crear la tabla con los productos
        # Encabezados de la tabla
        datos_tabla = [['Cantidad', 'Producto', 'Precio Unit.', 'Subtotal']]
        # Añadir las filas del carrito
        for item in items_carrito:
            datos_tabla.append(item)
        
        tabla = Table(datos_tabla)

        # Estilo de la tabla
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkslategray),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            # Alinear columnas de precios a la derecha
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'), 
            ('PADDING', (2,1), (-1,-1), 4)
        ])
        tabla.setStyle(style)
        
        story.append(tabla)
        story.append(Spacer(1, 24))

        # Total final
        style_total = ParagraphStyle(name='TotalStyle', parent=styles['h3'], alignment=TA_RIGHT)
        story.append(Paragraph(f"<b>Total a Pagar: {total_str}</b>", style_total))
        story.append(Spacer(1, 12))
        story.append(Paragraph("¡Gracias por su compra!", styles['Italic']))

        # 5. Generar (construir) el archivo PDF
        doc.build(story)
        
        return ruta_archivo

    except Exception as e:
        print(f"Error al generar el PDF: {e}")
        return None

def crear_recibo_con_secciones(nombre_restaurante, items_por_seccion, total_general, folio_numero=None):
    """
    Crea un recibo PDF con secciones organizadas.
    
    :param nombre_restaurante: Nombre del cliente/restaurante
    :param items_por_seccion: Dict con formato:
        {
            "Nombre Sección": {
                "items": [["cantidad", "producto", "precio_unit", "subtotal"], ...],
                "subtotal": float
            }
        }
    :param total_general: Total general de todas las secciones
    :param folio_numero: Número de folio del recibo
    :return: Ruta del archivo PDF creado o None si hay error
    """
    try:
        # 1. Crear el directorio 'recibos' si no existe
        os.makedirs(DIRECTORIO_RECIBOS, exist_ok=True)

        # 2. Generar un nombre de archivo único
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folio_suffix = f"_Folio_{folio_numero}" if folio_numero else ""
        nombre_archivo = f"Recibo_Seccionado_{nombre_restaurante.replace(' ', '_')}_{timestamp}{folio_suffix}.pdf"
        ruta_archivo = os.path.join(DIRECTORIO_RECIBOS, nombre_archivo)

        # 3. Configurar el documento PDF
        doc = SimpleDocTemplate(ruta_archivo, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # 4. Construir el contenido del PDF
        # Header con título y folio
        if folio_numero:
            # Crear tabla para header con folio en esquina superior derecha
            header_data = [["Bodega de Insumos 'Disfruleg'", f"FOLIO: {folio_numero:06d}"]]
            header_table = Table(header_data, colWidths=[400, 150])
            header_style = TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (0, 0), 18),
                ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (1, 0), (1, 0), 14),
                ('TEXTCOLOR', (1, 0), (1, 0), colors.red),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ])
            header_table.setStyle(header_style)
            story.append(header_table)
        else:
            # Título principal sin folio
            story.append(Paragraph("Bodega de Insumos 'Disfruleg'", styles['h1']))
        
        story.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
        story.append(Spacer(1, 24))

        # Información del cliente
        story.append(Paragraph(f"<b>Recibo para:</b> {nombre_restaurante}", styles['h2']))
        story.append(Spacer(1, 12))

        # Procesar cada sección
        for nombre_seccion, datos_seccion in items_por_seccion.items():
            # Título de la sección
            style_seccion = ParagraphStyle(
                name='SeccionStyle', 
                parent=styles['h3'], 
                alignment=TA_CENTER,
                backColor=colors.lightgrey,
                borderPadding=8
            )
            story.append(Paragraph(f"═══ {nombre_seccion.upper()} ═══", style_seccion))
            story.append(Spacer(1, 8))

            # Tabla de productos de la sección
            items_seccion = datos_seccion['items']
            if items_seccion:
                # Encabezados de la tabla
                datos_tabla = [['Cantidad', 'Producto', 'Precio Unit.', 'Subtotal']]
                datos_tabla.extend(items_seccion)
                
                tabla = Table(datos_tabla)
                
                # Estilo de la tabla
                style_tabla = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkslategray),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),  # Precios alineados a la derecha
                    ('PADDING', (0, 0), (-1, -1), 4)
                ])
                tabla.setStyle(style_tabla)
                
                story.append(tabla)
                story.append(Spacer(1, 8))

                # Subtotal de la sección
                subtotal_seccion = datos_seccion['subtotal']
                style_subtotal = ParagraphStyle(
                    name='SubtotalStyle', 
                    parent=styles['Normal'], 
                    alignment=TA_RIGHT,
                    fontName='Helvetica-Bold'
                )
                story.append(Paragraph(f"Subtotal {nombre_seccion}: ${subtotal_seccion:.2f}", style_subtotal))
                story.append(Spacer(1, 16))

        # Línea separadora antes del total
        story.append(Paragraph("─" * 80, styles['Normal']))
        story.append(Spacer(1, 12))

        # Total general
        style_total = ParagraphStyle(
            name='TotalStyle', 
            parent=styles['h2'], 
            alignment=TA_RIGHT,
            textColor=colors.darkgreen,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph(f"<b>TOTAL GENERAL: ${total_general:.2f}</b>", style_total))
        story.append(Spacer(1, 12))
        story.append(Paragraph("¡Gracias por su compra!", styles['Italic']))

        # 5. Generar el archivo PDF
        doc.build(story)
        
        return ruta_archivo

    except Exception as e:
        print(f"Error al generar el PDF con secciones: {e}")
        return None

# Función auxiliar para convertir datos del carrito con secciones a formato simple
def convertir_secciones_a_simple(items_por_seccion):
    """
    Convierte datos organizados por secciones a formato simple para compatibilidad.
    """
    items_simple = []
    for nombre_seccion, datos_seccion in items_por_seccion.items():
        for item in datos_seccion['items']:
            items_simple.append(item)
    return items_simple

# Función de conveniencia que detecta automáticamente el tipo de recibo
def crear_recibo_automatico(nombre_restaurante, items_carrito=None, items_por_seccion=None, total=None):
    """
    Crea un recibo detectando automáticamente si usar secciones o no.
    """
    if items_por_seccion and len(items_por_seccion) > 1:
        # Hay múltiples secciones, usar formato con secciones
        if isinstance(total, str):
            total_float = float(total.replace('$', '').replace(',', ''))
        else:
            total_float = float(total)
        
        return crear_recibo_con_secciones(nombre_restaurante, items_por_seccion, total_float)
    else:
        # Una sola sección o formato simple, usar formato original
        if items_carrito is None and items_por_seccion:
            # Convertir de secciones a formato simple
            items_carrito = convertir_secciones_a_simple(items_por_seccion)
        
        if isinstance(total, (int, float)):
            total_str = f"${total:.2f}"
        else:
            total_str = str(total)
        
        return crear_recibo_simple(nombre_restaurante, items_carrito, total_str)