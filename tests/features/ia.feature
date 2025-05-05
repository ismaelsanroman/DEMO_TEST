# tests/features/micro_ia/ia.feature

@micro_ia @bdd @feature_ia_respuestas
@allure.label.epic=Microservicios_Bancarios
@allure.label.feature=IA
@allure.label.owner=Ismael
@allure.id=T003
Feature: Microservicio de IA
  Este micro utiliza IA simulada para interpretar y responder a consultas generales relacionadas con productos y operaciones bancarias.

  Background:
    Given que tengo un token válido
    And la URL del micro "ia"

  @smoke @regression
    @allure.severity=normal
    @allure.label.story=Respuestas_generadas_por_IA
    @allure.label.microservicio=ia
    @allure.label.tipo=bdd
  Scenario Outline: Respuestas de IA según palabra clave
    When envío una petición POST a "/respuesta" con pregunta "<pregunta>"
    Then el código de respuesta debe ser 200
    And la respuesta debe contener "<esperado>"

    Examples:
      | pregunta                                       | esperado                 |
      | ¿Qué tipo de interés tienen las hipotecas?     | 3,2%                     |
      | Necesito solicitar una nueva tarjeta           | tarjeta                  |
      | Hazme una transferencia mañana                 | 24h hábiles              |
      | ¿Cuál es la comisión de mantenimiento?         | 10€                      |
      | ¿Cuál es el horario de la oficina más cercana? | lunes a viernes          |
      | ¿Cómo descargo mi certificado bancario?        | descargar tu certificado |
      | Quiero información sobre un préstamo personal  | 5,5%                     |
      | ¿Qué opciones de inversión tenéis?             | planes de inversión      |
      | ¿Cuál es la velocidad de la luz?               | Lo siento                |
