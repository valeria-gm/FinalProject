USE market;

-- Trigger para registrar deuda automáticamente al crear factura
DELIMITER //
CREATE TRIGGER after_detalle_insert_update_deuda
AFTER INSERT ON detalle_factura
FOR EACH ROW
BEGIN
    -- Actualizar o crear la deuda cada vez que se agrega un detalle
    INSERT INTO deuda (id_cliente, id_factura, monto, fecha_generada, monto_pagado, pagado, descripcion)
    SELECT 
        f.id_cliente,
        f.id_factura,
        SUM(df.cantidad_factura * df.precio_unitario_venta),
        CURDATE(),
        0.00,
        FALSE,
        CONCAT('Deuda por factura #', f.id_factura)
    FROM factura f
    JOIN detalle_factura df ON f.id_factura = df.id_factura
    WHERE f.id_factura = NEW.id_factura
    GROUP BY f.id_cliente, f.id_factura
    ON DUPLICATE KEY UPDATE
        monto = VALUES(monto);
END //
DELIMITER ;

-- Trigger para evitar modificación de órdenes registradas
DELIMITER //
CREATE TRIGGER before_orden_update
BEFORE UPDATE ON ordenes_guardadas
FOR EACH ROW
BEGIN
    IF OLD.estado = 'registrada' AND NEW.estado != OLD.estado THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'No se puede modificar una orden ya registrada';
    END IF;
    
    -- Actualizar automáticamente la fecha de modificación
    SET NEW.fecha_modificacion = CURRENT_TIMESTAMP;
END //
DELIMITER ;

-- Trigger para actualizar stock al registrar compras
DELIMITER //
CREATE TRIGGER after_compra_insert
AFTER INSERT ON compra
FOR EACH ROW
BEGIN
    UPDATE producto 
    SET stock = stock + NEW.cantidad_compra
    WHERE id_producto = NEW.id_producto;
END //
DELIMITER ;

-- Trigger para validar eliminación de órdenes activas
DELIMITER //
CREATE TRIGGER before_orden_delete
BEFORE DELETE ON ordenes_guardadas
FOR EACH ROW
BEGIN
    -- Prevenir eliminación física de órdenes registradas
    IF OLD.estado = 'registrada' THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'No se pueden eliminar órdenes registradas. Use soft delete (activo = FALSE)';
    END IF;
END //
DELIMITER ;

-- Trigger para validar datos de carrito JSON antes de insertar (CORREGIDO)
DELIMITER //
CREATE TRIGGER before_orden_insert_validate
BEFORE INSERT ON ordenes_guardadas
FOR EACH ROW
BEGIN
    DECLARE mensaje_error TEXT;
    
    -- Validar que datos_carrito sea JSON válido
    IF NOT JSON_VALID(NEW.datos_carrito) THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Los datos del carrito deben ser un JSON válido';
    END IF;
    
    -- Validar que el total estimado sea positivo
    IF NEW.total_estimado <= 0 THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'El total estimado debe ser mayor que cero';
    END IF;
    
    -- Asegurar que el usuario existe
    IF NOT EXISTS (SELECT 1 FROM usuarios_sistema WHERE username = NEW.usuario_creador AND activo = TRUE) THEN
        SET mensaje_error = CONCAT('Usuario no válido: ', NEW.usuario_creador);
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = mensaje_error;
    END IF;
END //
DELIMITER ;