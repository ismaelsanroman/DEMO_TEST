# tests/features/micro_orquestador/orquestador.feature

@micro_orquestador @bdd @feature_orquestador
@allure.label.epic=Microservicios_Bancarios
@allure.label.feature=Orquestador
@allure.label.owner=Ismael
@allure.id=T005
Feature: Microservicio Orquestador
  Este micro es responsable de orquestar y enrutar las preguntas del usuario al microservicio especialista adecuado.

  Background:
    Given que tengo un token válido
    And la URL del micro "orquestador"

  @smoke @feature_token
  @allure.severity=critical
  @allure.label.story=Autenticacion_y_tokens
  @allure.label.microservicio=orquestador
  @allure.label.tipo=bdd
  Scenario: Obtener token
    When envío una petición POST a "/token" sin payload
    Then el código de respuesta debe ser 200
    And la respuesta debe contener "access_token"

  @smoke @regression @feature_routing
    @allure.severity=normal
    @allure.label.story=Enrutamiento_de_consultas
    @allure.label.microservicio=orquestador
    @allure.label.tipo=bdd
  Scenario Outline: Enrutamiento de consultas
    When envío una petición POST a "/consulta" con pregunta "<pregunta>"
    Then el código de respuesta debe ser 200
    And la respuesta debe contener "<esperado>"

    Examples:
      | pregunta                                | esperado                   |
      | ¿Qué he comprado últimamente?           | compra de 35€              |
      | ¿Cuál es mi saldo actual?               | saldo actual es de         |
      #| Necesito abrir una cuenta nueva         | cuenta ha sido abierta     |
      | Por favor verifica mi DNI               | documento ha sido validado |
      | ¿Qué tipo de interés tiene la hipoteca? | 3,2%                       |
      | ¿Cuál es el color del cielo?            | lo siento                  |
