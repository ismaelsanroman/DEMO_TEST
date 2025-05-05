# tests/features/micro_identidad/identidad.feature

@micro_identidad @bdd @feature_verificacion_identidad
@allure.label.epic=Microservicios_Bancarios
@allure.label.feature=Identidad
@allure.label.owner=Ismael
@allure.id=T004
Feature: Microservicio de Identidad
  Este micro valida documentos y mecanismos de autenticación del usuario (DNI, SMS, correo electrónico, 2FA…).

  Background:
    Given que tengo un token válido
    And la URL del micro "identidad"

  @smoke @regression
    @allure.severity=normal
    @allure.label.story=Verificacion_de_identidad
    @allure.label.microservicio=identidad
    @allure.label.tipo=bdd
  Scenario Outline: Verificación de identidad
    When envío una petición POST a "/respuesta" con pregunta "<pregunta>"
    Then el código de respuesta debe ser 200
    And la respuesta debe contener "<esperado>"

    Examples:
      | pregunta                                  | esperado                                                          |
      | ¿Puedes verificar mi DNI?                 | Tu documento ha sido validado correctamente                        |
      | Necesito un código SMS para continuar     | Código verificado correctamente                                    |
      | Por favor confirma mi correo electrónico  | Tu correo ha sido confirmado                                       |
      | Activa la autenticación de dos factores   | Autenticación en dos pasos completada correctamente                |
      | Verificar identidad del usuario           | Identidad verificada con éxito                                     |
      | ¿Cómo está el tiempo hoy?                 | No se ha podido determinar el tipo de verificación                 |
