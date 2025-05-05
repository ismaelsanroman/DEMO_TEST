# tests/features/micro_consultas/consultas.feature

@micro_consultas @bdd @feature_respuestas
@allure.label.epic=Microservicios_Bancarios
@allure.label.feature=Consultas
@allure.label.owner=Ismael
@allure.id=T001
Feature: Microservicio de Consultas
  Este micro devuelve respuestas relacionadas con movimientos, saldos, extractos, cajeros y más.

  Background:
    Given que tengo un token válido
    And la URL del micro "consultas"

  @smoke @regression
    @allure.severity=normal
    @allure.label.story=Respuestas_preguntas_frecuentes
    @allure.label.microservicio=consultas
    @allure.label.tipo=bdd
  Scenario Outline: Respuestas según pregunta
    When envío una petición POST a "/respuesta" con pregunta "<pregunta>"
    Then el código de respuesta debe ser 200
    And la respuesta debe contener "<esperado>"

    Examples:
      | pregunta                              | esperado                         |
      | ¿Qué he comprado últimamente?         | compra de 35€                    |
      | ¿Cuál es mi saldo actual?             | saldo actual es de               |
      | Muéstrame mi extracto de cuenta       | extracto de abril                |
      | Quiero ver mi recibo de luz           | último recibo de internet        |
      | Necesito mi IBAN                      | IBAN es ES6600190020961234567890 |
      | ¿Dónde está el cajero más cercano?    | Dónde estamos                    |
      | Informarme sobre el ingreso de dinero | ingreso de 1.200€                |
      | ¿Cuál es el límite de mi tarjeta?     | límite de tu tarjeta             |
      | Dime el tipo de cambio EUR/USD        | tipo de cambio actual            |
      | ¿Cuándo fue mi último acceso?         | Tu último acceso fue             |
      | ¿Cuál es la capital de Fantasía?      | No tengo información suficiente  |
