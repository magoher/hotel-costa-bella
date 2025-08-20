-- Schema para sistema de reservas (MySQL 8+)
CREATE DATABASE IF NOT EXISTS hotel_reservas CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE hotel_reservas;

-- 1) Catálogos
CREATE TABLE IF NOT EXISTS room_types (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  name            VARCHAR(100) NOT NULL UNIQUE,
  capacity        INT          NOT NULL CHECK (capacity > 0),
  price_per_night DECIMAL(10,2) NOT NULL CHECK (price_per_night >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS rooms (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  room_type_id  INT NOT NULL,
  number        VARCHAR(20) NOT NULL UNIQUE,
  status        ENUM('Disponible','Ocupada','Mantenimiento') NOT NULL DEFAULT 'Disponible',
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (room_type_id) REFERENCES room_types(id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  INDEX (status),
  INDEX (room_type_id)
) ENGINE=InnoDB;

-- 2) Entidades de negocio
CREATE TABLE IF NOT EXISTS guests (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  first_name  VARCHAR(100) NOT NULL,
  last_name   VARCHAR(100) NOT NULL,
  email       VARCHAR(150) NOT NULL,
  phone       VARCHAR(30),
  UNIQUE KEY uq_guest_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS reservations (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  guest_id      INT NOT NULL,
  room_id       INT NOT NULL,
  check_in      DATE NOT NULL,
  check_out     DATE NOT NULL,
  adults        INT NOT NULL CHECK (adults > 0),
  children      INT NOT NULL DEFAULT 0 CHECK (children >= 0),
  status        ENUM('Pendiente','Confirmada','Cancelada','NoShow','Completada') NOT NULL DEFAULT 'Pendiente',
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (guest_id) REFERENCES guests(id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  FOREIGN KEY (room_id) REFERENCES rooms(id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CHECK (check_out > check_in),
  INDEX idx_res_room_dates (room_id, check_in, check_out),
  INDEX idx_res_guest (guest_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS payments (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  reservation_id  INT NOT NULL,
  amount          DECIMAL(10,2) NOT NULL CHECK (amount >= 0),
  currency        CHAR(3) NOT NULL DEFAULT 'USD',
  method          ENUM('Tarjeta','Efectivo','Transferencia','Otro') NOT NULL,
  paid_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (reservation_id) REFERENCES reservations(id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  INDEX (reservation_id)
) ENGINE=InnoDB;

-- 3) Integración (opcional) clima para dashboards
CREATE TABLE IF NOT EXISTS weather_daily (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  day       DATE NOT NULL UNIQUE,
  t_min     DECIMAL(5,2),
  t_max     DECIMAL(5,2),
  cond_text VARCHAR(80)
) ENGINE=InnoDB;

-- 4) Reglas de disponibilidad (vista + función + SP)
-- Vista: reservas activas por habitación en una fecha dada (ej. hoy)
CREATE OR REPLACE VIEW v_room_status_today AS
SELECT
  r.id AS room_id,
  r.number,
  r.status AS room_status,
  COALESCE((
      SELECT res.status
      FROM reservations res
      WHERE res.room_id = r.id
        AND CURRENT_DATE() < res.check_out
        AND CURRENT_DATE() >= res.check_in
        AND res.status IN ('Pendiente','Confirmada')
      ORDER BY res.id DESC
      LIMIT 1
  ), 'Libre') AS occupancy_today
FROM rooms r;

-- Función: detecta traslape de fechas con una reserva existente
DROP FUNCTION IF EXISTS overlaps;
DELIMITER $$
CREATE FUNCTION overlaps(a_start DATE, a_end DATE, b_start DATE, b_end DATE)
RETURNS TINYINT DETERMINISTIC
BEGIN
  RETURN (a_start < b_end) AND (a_end > b_start);
END$$
DELIMITER ;

-- Procedimiento: intenta reservar respetando disponibilidad
DROP PROCEDURE IF EXISTS sp_book_reservation;
DELIMITER $$
CREATE PROCEDURE sp_book_reservation(
  IN p_first_name VARCHAR(100),
  IN p_last_name  VARCHAR(100),
  IN p_email      VARCHAR(150),
  IN p_phone      VARCHAR(30),
  IN p_room_id    INT,
  IN p_check_in   DATE,
  IN p_check_out  DATE,
  IN p_adults     INT,
  IN p_children   INT
)
BEGIN
  DECLARE v_guest_id INT;
  DECLARE v_conflicts INT;

  START TRANSACTION;

  -- upsert invitado
  SELECT id INTO v_guest_id FROM guests WHERE email = p_email LIMIT 1;
  IF v_guest_id IS NULL THEN
    INSERT INTO guests(first_name,last_name,email,phone)
    VALUES(p_first_name,p_last_name,p_email,p_phone);
    SET v_guest_id = LAST_INSERT_ID();
  END IF;

  -- verificar traslapes
  SELECT COUNT(*) INTO v_conflicts
  FROM reservations
  WHERE room_id = p_room_id
    AND status IN ('Pendiente','Confirmada')
    AND overlaps(p_check_in, p_check_out, check_in, check_out);

  IF v_conflicts > 0 THEN
    ROLLBACK;
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La habitación no está disponible para ese rango';
  END IF;

  INSERT INTO reservations(guest_id, room_id, check_in, check_out, adults, children, status)
  VALUES(v_guest_id, p_room_id, p_check_in, p_check_out, p_adults, p_children, 'Confirmada');

  COMMIT;
END$$
DELIMITER ;

-- 5) Seed (ejemplo)
INSERT IGNORE INTO room_types(name, capacity, price_per_night) VALUES
  ('Estandar', 2, 65.00), ('Suite', 4, 120.00), ('Deluxe', 3, 90.00);

INSERT IGNORE INTO rooms(room_type_id, number, status) VALUES
  (1,'101','Disponible'), (1,'102','Disponible'), (2,'201','Disponible'),
  (3,'301','Mantenimiento');

-- Reserva de muestra (si no hay)
INSERT IGNORE INTO guests(first_name,last_name,email,phone)
VALUES ('Ana','Ramírez','ana@example.com','+50660001111');

INSERT IGNORE INTO reservations(guest_id, room_id, check_in, check_out, adults, children, status)
SELECT g.id, 1, CURDATE()+INTERVAL 3 DAY, CURDATE()+INTERVAL 6 DAY, 2, 0, 'Confirmada'
FROM guests g WHERE g.email='ana@example.com' LIMIT 1;
