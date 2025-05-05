# tests/features/micro_cuentas/cuentas.feature

@micro_cuentas @bdd @feature_respuestas
@allure.label.epic=Microservicios_Bancarios
@allure.label.feature=Cuentas
@allure.label.owner=Ismael
@allure.id=T002
Feature: Microservicio de Cuentas
  Este micro gestiona acciones relacionadas con la apertura, tipos y condiciones de cuentas bancarias.

  Background:
    Given que tengo un token válido
    And la URL del micro "cuentas"

  @smoke @regression
    @allure.severity=normal
    @allure.label.story=Respuestas_sobre_productos_bancarios
    @allure.label.microservicio=cuentas
    @allure.label.tipo=bdd
  Scenario Outline: Respuestas según pregunta
    When envío una petición POST a "/respuesta" con pregunta "<pregunta>"
    Then el código de respuesta debe ser 200
    And la respuesta debe contener "<esperado>"

    Examples:
      | pregunta                                        | esperado                                                   |
      #| Quiero abrir cuenta                             | Tu cuenta ha sido abierta correctamente                     |
      | ¿Qué tipo de cuenta ofrecéis?                   | Ofrecemos cuentas corrientes, cuentas nómina                |
      #| Cuáles son los requisitos para abrir una cuenta | Para abrir una cuenta necesitas ser mayor de edad           |
      | Dime las comisiones                             | Las cuentas estándar no tienen comisiones                   |
      | Necesito cambiar cuenta                         | Podemos ayudarte a convertir tu cuenta actual               |
      | ¿Cuál es el plazo de apertura?                  | El proceso de apertura es inmediato                         |
      | ¿Tienen horario de atención?                    | No he encontrado información sobre eso                      |
