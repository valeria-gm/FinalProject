USE market;

-- Vista para detalle de factura con descuento (DEBE IR PRIMERO)
CREATE OR REPLACE VIEW vista_detalle_factura_con_descuento AS
SELECT 
    df.id_detalle,
    df.id_factura,
    df.id_producto,
    p.nombre_producto,
    p.unidad_producto,
    df.cantidad_factura,
    pg.precio_base AS precio_base_grupo,
    tc.descuento AS porcentaje_descuento,
    ROUND(pg.precio_base * (1 - tc.descuento/100), 2) AS precio_unitario_calculado,
    df.precio_unitario_venta AS precio_registrado,
    ROUND(df.cantidad_factura * pg.precio_base * (1 - tc.descuento/100), 2) AS subtotal_con_descuento,
    c.id_grupo,
    g.clave_grupo,
    tc.id_tipo_cliente,
    tc.nombre_tipo AS tipo_cliente,
    sf.nombre_seccion,
    sf.orden_seccion
FROM detalle_factura df
JOIN factura f ON df.id_factura = f.id_factura
JOIN cliente c ON f.id_cliente = c.id_cliente
JOIN grupo g ON c.id_grupo = g.id_grupo
JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
JOIN producto p ON df.id_producto = p.id_producto
JOIN precio_por_grupo pg ON p.id_producto = pg.id_producto AND c.id_grupo = pg.id_grupo
LEFT JOIN seccion_factura sf ON df.id_seccion = sf.id_seccion;

-- Vista para estado de cuenta por cliente
CREATE OR REPLACE VIEW vista_estado_cuenta_cliente AS
SELECT 
    c.id_cliente,
    c.nombre_cliente,
    g.clave_grupo,
    tc.nombre_tipo AS tipo_cliente,
    SUM(CASE WHEN d.pagado = FALSE THEN d.monto - d.monto_pagado ELSE 0 END) AS saldo_pendiente,
    SUM(CASE WHEN d.pagado = FALSE THEN d.monto ELSE 0 END) AS total_deuda_pendiente,
    SUM(CASE WHEN d.pagado = TRUE THEN d.monto ELSE 0 END) AS total_deuda_pagada,
    COUNT(DISTINCT CASE WHEN d.pagado = FALSE THEN d.id_deuda ELSE NULL END) AS deudas_pendientes,
    COUNT(DISTINCT CASE WHEN d.pagado = TRUE THEN d.id_deuda ELSE NULL END) AS deudas_pagadas,
    MAX(CASE WHEN d.pagado = FALSE THEN d.fecha_generada ELSE NULL END) AS ultima_deuda_generada,
    MAX(CASE WHEN d.pagado = TRUE THEN d.fecha_pago ELSE NULL END) AS ultimo_pago,
    CASE 
        WHEN SUM(CASE WHEN d.pagado = FALSE THEN d.monto ELSE 0 END) = 0 THEN 'Al día'
        WHEN SUM(CASE WHEN d.pagado = FALSE THEN d.monto - d.monto_pagado ELSE 0 END) > 0 THEN 'Con deuda'
        ELSE 'Situación desconocida'
    END AS estado_cuenta
FROM cliente c
LEFT JOIN deuda d ON c.id_cliente = d.id_cliente
LEFT JOIN grupo g ON c.id_grupo = g.id_grupo
LEFT JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
GROUP BY c.id_cliente, c.nombre_cliente, g.clave_grupo, tc.nombre_tipo;

-- Vista detallada de deudas por cliente
CREATE OR REPLACE VIEW vista_deudas_detalladas AS
SELECT 
    d.id_deuda,
    c.id_cliente,
    c.nombre_cliente,
    f.id_factura,
    f.fecha_factura,
    d.monto AS monto_total,
    d.monto_pagado,
    d.monto - d.monto_pagado AS saldo_pendiente,
    d.fecha_generada,
    d.fecha_pago,
    d.pagado,
    d.descripcion,
    DATEDIFF(CURRENT_DATE, d.fecha_generada) AS dias_pendiente,
    CASE 
        WHEN d.pagado THEN 'Pagada'
        WHEN d.monto_pagado > 0 THEN 'Parcialmente pagada'
        ELSE 'Pendiente'
    END AS estado_deuda,
    g.clave_grupo,
    tc.nombre_tipo AS tipo_cliente
FROM deuda d
JOIN cliente c ON d.id_cliente = c.id_cliente
JOIN factura f ON d.id_factura = f.id_factura
JOIN grupo g ON c.id_grupo = g.id_grupo
JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente;

-- Vista para historial de pagos
CREATE OR REPLACE VIEW vista_historial_pagos AS
SELECT
    d.id_deuda,
    c.id_cliente,
    c.nombre_cliente,
    f.id_factura,
    f.folio_numero,
    d.monto AS monto_total,
    d.monto_pagado,
    d.fecha_pago,
    d.metodo_pago,
    d.referencia_pago,
    u.username AS registrado_por,
    d.descripcion,
    g.clave_grupo,
    tc.nombre_tipo AS tipo_cliente
FROM deuda d
JOIN cliente c ON d.id_cliente = c.id_cliente
JOIN factura f ON d.id_factura = f.id_factura
JOIN grupo g ON c.id_grupo = g.id_grupo
JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
LEFT JOIN usuarios_sistema u ON d.descripcion LIKE CONCAT('%Operador:%', u.username, '%')
WHERE d.pagado = TRUE;

-- Vista para ganancias por cliente 
CREATE OR REPLACE VIEW vista_ganancias_por_cliente AS
SELECT 
    c.id_cliente,
    c.nombre_cliente,
    g.clave_grupo,
    tc.nombre_tipo AS tipo_cliente,
    tc.descuento AS porcentaje_descuento,
    SUM(vd.subtotal_con_descuento) AS total_ventas,
    COUNT(DISTINCT f.id_factura) AS cantidad_facturas,
    MAX(f.fecha_factura) AS ultima_compra,
    SUM(CASE WHEN d.pagado = FALSE THEN d.monto - d.monto_pagado ELSE 0 END) AS saldo_pendiente
FROM cliente c
JOIN factura f ON c.id_cliente = f.id_cliente
JOIN detalle_factura df ON f.id_factura = df.id_factura
JOIN vista_detalle_factura_con_descuento vd ON df.id_detalle = vd.id_detalle
JOIN grupo g ON c.id_grupo = g.id_grupo
JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
LEFT JOIN deuda d ON f.id_factura = d.id_factura
GROUP BY c.id_cliente, c.nombre_cliente, g.clave_grupo, tc.nombre_tipo, tc.descuento;

-- Vista para órdenes pendientes
CREATE OR REPLACE VIEW vista_ordenes_pendientes AS
SELECT 
    og.id_orden,
    og.folio_numero,
    c.id_cliente,
    c.nombre_cliente,
    og.usuario_creador,
    u.nombre_completo AS nombre_usuario,
    og.fecha_creacion,
    og.fecha_modificacion,
    og.total_estimado,
    og.estado,
    JSON_EXTRACT(og.datos_carrito, '$.productos') AS productos_json,
    g.clave_grupo,
    tc.nombre_tipo AS tipo_cliente
FROM ordenes_guardadas og
JOIN cliente c ON og.id_cliente = c.id_cliente
JOIN usuarios_sistema u ON og.usuario_creador = u.username
JOIN grupo g ON c.id_grupo = g.id_grupo
JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
WHERE og.activo = TRUE AND og.estado = 'guardada';

-- Vista para ganancias por grupo
CREATE OR REPLACE VIEW vista_ganancias_por_grupo AS
SELECT 
    g.id_grupo,
    g.clave_grupo,
    tc.nombre_tipo AS tipo_cliente,
    COUNT(DISTINCT c.id_cliente) AS cantidad_clientes,
    SUM(vd.subtotal_con_descuento) AS total_ventas,
    COUNT(DISTINCT f.id_factura) AS cantidad_facturas,
    tc.descuento AS descuento_aplicado,
    ROUND(AVG(vd.subtotal_con_descuento / NULLIF(vd.cantidad_factura, 0)), 2) AS ticket_promedio
FROM grupo g
LEFT JOIN cliente c ON g.id_grupo = c.id_grupo
LEFT JOIN factura f ON c.id_cliente = f.id_cliente
LEFT JOIN detalle_factura df ON f.id_factura = df.id_factura
LEFT JOIN vista_detalle_factura_con_descuento vd ON df.id_detalle = vd.id_detalle
LEFT JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
GROUP BY g.id_grupo, g.clave_grupo, tc.nombre_tipo, tc.descuento;

-- Vista para ganancias por producto y grupo
CREATE OR REPLACE VIEW vista_ganancias_por_producto_grupo AS
SELECT 
    p.id_producto,
    p.nombre_producto,
    g.id_grupo,
    g.clave_grupo,
    tc.nombre_tipo AS tipo_cliente,
    SUM(df.cantidad_factura) AS cantidad_vendida,
    SUM(vd.subtotal_con_descuento) AS ingresos_totales,
    ROUND(SUM(vd.subtotal_con_descuento) / NULLIF(SUM(df.cantidad_factura), 0), 2) AS precio_promedio,
    COALESCE(SUM(c.cantidad_compra), 0) AS cantidad_comprada,
    COALESCE(SUM(c.cantidad_compra * c.precio_unitario_compra), 0) AS costos_totales,
    SUM(vd.subtotal_con_descuento) - COALESCE(SUM(c.cantidad_compra * c.precio_unitario_compra), 0) AS ganancia_total,
    CASE 
        WHEN COALESCE(SUM(c.cantidad_compra * c.precio_unitario_compra), 0) = 0 THEN 0
        ELSE ROUND(((SUM(vd.subtotal_con_descuento) - 
                    COALESCE(SUM(c.cantidad_compra * c.precio_unitario_compra), 0)) / 
                    COALESCE(SUM(c.cantidad_compra * c.precio_unitario_compra), 0)) * 100, 2)
    END AS margen_ganancia_porcentaje
FROM producto p
LEFT JOIN detalle_factura df ON p.id_producto = df.id_producto
LEFT JOIN vista_detalle_factura_con_descuento vd ON df.id_detalle = vd.id_detalle
LEFT JOIN factura f ON df.id_factura = f.id_factura
LEFT JOIN cliente cl ON f.id_cliente = cl.id_cliente
LEFT JOIN grupo g ON cl.id_grupo = g.id_grupo
LEFT JOIN tipo_cliente tc ON g.id_tipo_cliente = tc.id_tipo_cliente
LEFT JOIN compra c ON p.id_producto = c.id_producto
GROUP BY p.id_producto, p.nombre_producto, g.id_grupo, g.clave_grupo, tc.nombre_tipo;

-- Vista para ganancias por producto (completa con stock)
CREATE OR REPLACE VIEW vista_ganancias_por_producto AS
SELECT 
    p.id_producto,
    p.nombre_producto,
    p.unidad_producto,
    SUM(df.cantidad_factura) AS cantidad_vendida,
    SUM(vd.subtotal_con_descuento) AS ingresos_totales,
    COALESCE(SUM(c.cantidad_compra), 0) AS cantidad_comprada,
    COALESCE(SUM(c.cantidad_compra * c.precio_unitario_compra), 0) AS costos_totales,
    SUM(vd.subtotal_con_descuento) - COALESCE(SUM(c.cantidad_compra * c.precio_unitario_compra), 0) AS ganancia_total,
    CASE 
        WHEN COALESCE(SUM(c.cantidad_compra * c.precio_unitario_compra), 0) = 0 THEN 0
        ELSE ROUND(((SUM(vd.subtotal_con_descuento) - 
                    COALESCE(SUM(c.cantidad_compra * c.precio_unitario_compra), 0)) / 
                    COALESCE(SUM(c.cantidad_compra * c.precio_unitario_compra), 0)) * 100, 2)
    END AS margen_ganancia_porcentaje,
    p.stock,
    ROUND(p.stock / NULLIF(AVG(df.cantidad_factura), 0), 1) AS meses_inventario
FROM producto p
LEFT JOIN detalle_factura df ON p.id_producto = df.id_producto
LEFT JOIN vista_detalle_factura_con_descuento vd ON df.id_detalle = vd.id_detalle
LEFT JOIN compra c ON p.id_producto = c.id_producto
GROUP BY p.id_producto, p.nombre_producto, p.unidad_producto, p.stock;