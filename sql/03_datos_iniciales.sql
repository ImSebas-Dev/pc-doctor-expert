-- Roles y casos de prueba (uno por hipótesis, con los hechos de su regla de diagnóstico)
INSERT INTO tx.rol(nombre,descripcion) VALUES
 ('usuario','Registra equipos, realiza diagnósticos y consulta su historial.'),
 ('administrador','Gestiona la base de conocimiento, los usuarios y los casos de prueba.');
INSERT INTO tx.caso_prueba(nombre,hipotesis_esperada_id) SELECT 'CP-'||codigo, id FROM kb.hipotesis ORDER BY codigo;
INSERT INTO tx.caso_prueba_hecho
 SELECT cp.id, c.hecho_id, c.valor FROM tx.caso_prueba cp
 JOIN kb.regla r ON r.hipotesis_id = cp.hipotesis_esperada_id AND r.tipo='diagnostico'
 JOIN kb.regla_condicion c ON c.regla_id = r.id;
