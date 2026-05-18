"""
Módulo de Facturación Electrónica DIAN - Colombia
Genera XML UBL 2.1, CUFE y código QR conforme al Anexo Técnico DIAN v1.9
"""

import hashlib
import base64
import io
from datetime import datetime
from zoneinfo import ZoneInfo

ZONA_COLOMBIA = ZoneInfo("America/Bogota")


def _fmt(valor):
    """Formatea valor numérico para cadena CUFE (2 decimales, punto decimal)."""
    return f"{float(valor or 0):.2f}"


def _escape_xml(text):
    """Escapa caracteres especiales XML."""
    if not text:
        return ''
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))


def _limpiar_nit(nit_raw):
    """Extrae solo los dígitos del NIT sin dígito de verificación."""
    if not nit_raw:
        return '', '0'
    partes = nit_raw.replace('.', '').replace(' ', '').split('-')
    nit = partes[0].strip()
    dv = partes[1].strip() if len(partes) > 1 else '0'
    return nit, dv


def generar_cufe(factura, nit_emisor, clave_tecnica, tipo_ambiente="2"):
    """
    CUFE = SHA-384(NumFac+FecFac+HorFac+ValFac+CodImp1+ValImp1+
                   CodImp2+ValImp2+CodImp3+ValImp3+ValTot+
                   NitOFE+NumAdq+ClTec+TipoAmbie)

    Ref: Resolución DIAN 042 / Anexo Técnico v1.9 sección 8.3
    """
    fe = factura.fecha_emision
    if fe is None:
        fe = datetime.now(ZONA_COLOMBIA).replace(tzinfo=None)

    nit_limpio, _ = _limpiar_nit(nit_emisor)
    doc_cliente = (factura.cliente_documento or '').strip() or '222222222222'

    cadena = (
        factura.numero_consecutivo +            # NumFac
        fe.strftime('%Y-%m-%d') +               # FecFac
        fe.strftime('%H:%M:%S') + '-05:00' +   # HorFac (UTC-5 Colombia)
        _fmt(factura.subtotal) +                # ValFac (base sin impuestos)
        "01" + _fmt(factura.iva) +              # CodImp1=IVA + ValImp1
        "04" + "0.00" +                         # CodImp2=INC + ValImp2
        "03" + "0.00" +                         # CodImp3=ICA + ValImp3
        _fmt(factura.total) +                   # ValTot
        nit_limpio +                            # NitOFE (sin DV)
        doc_cliente +                           # NumAdq
        clave_tecnica +                         # ClTec
        tipo_ambiente                           # TipoAmbie: "1"=prod, "2"=hab
    )

    return hashlib.sha384(cadena.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------------------
# Número a letras (español colombiano)
# ---------------------------------------------------------------------------

_UNIDADES = [
    '', 'UN', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE',
    'DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE', 'DIECISÉIS',
    'DIECISIETE', 'DIECIOCHO', 'DIECINUEVE',
]
_DECENAS = [
    '', 'DIEZ', 'VEINTE', 'TREINTA', 'CUARENTA', 'CINCUENTA',
    'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA',
]
_CENTENAS = [
    '', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS',
    'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS',
]


def _numero_a_letras(n):
    n = int(n)
    if n == 0:
        return 'CERO'
    if n == 100:
        return 'CIEN'
    if n == 1000:
        return 'MIL'

    resultado = ''
    if n >= 1_000_000:
        m = n // 1_000_000
        r = n % 1_000_000
        resultado += ('UN MILLÓN' if m == 1 else _numero_a_letras(m) + ' MILLONES')
        if r:
            resultado += ' ' + _numero_a_letras(r)
        return resultado

    if n >= 1_000:
        miles = n // 1_000
        r = n % 1_000
        resultado += ('MIL' if miles == 1 else _numero_a_letras(miles) + ' MIL')
        if r:
            resultado += ' ' + _numero_a_letras(r)
        return resultado

    if n >= 100:
        c = n // 100
        r = n % 100
        resultado += _CENTENAS[c]
        if r:
            resultado += ' ' + _numero_a_letras(r)
        return resultado

    if n >= 20:
        d = n // 10
        u = n % 10
        resultado += _DECENAS[d]
        if u:
            resultado += ' Y ' + _UNIDADES[u]
        return resultado

    return _UNIDADES[n]


def valor_en_letras(total):
    """Retorna el total en letras como exige la DIAN en el campo Note."""
    entero = int(total)
    decimales = round((total - entero) * 100)
    letras = _numero_a_letras(entero)
    sufijo = f'CON {decimales}/100 ' if decimales else ''
    return f"{letras} PESOS {sufijo}M/CTE"


# ---------------------------------------------------------------------------
# Generación XML UBL 2.1
# ---------------------------------------------------------------------------

def generar_xml_ubl(factura, config, cufe, items, tipo_ambiente="2"):
    """
    Genera XML UBL 2.1 conforme al Anexo Técnico DIAN v1.9.

    Args:
        factura: objeto Factura de SQLAlchemy
        config:  objeto ConfiguracionRestaurante de SQLAlchemy
        cufe:    string CUFE ya calculado
        items:   lista de dicts:
                 {descripcion, cantidad, precio_unitario, subtotal,
                  iva_porcentaje, iva_valor}
        tipo_ambiente: "1"=producción, "2"=habilitación

    Returns:
        string XML codificado en UTF-8
    """
    fe = factura.fecha_emision or datetime.now(ZONA_COLOMBIA).replace(tzinfo=None)
    fecha_str = fe.strftime('%Y-%m-%d')
    hora_str = fe.strftime('%H:%M:%S') + '-05:00'

    # Datos emisor
    nit_emisor, dv_emisor = _limpiar_nit(config.nit or '900000000')
    nombre_emisor = _escape_xml(config.nombre or 'Restaurante')
    dir_emisor = _escape_xml(config.direccion or '')
    ciudad_nombre = _escape_xml(getattr(config, 'ciudad_nombre', None) or config.ciudad or '')
    dpto = _escape_xml(getattr(config, 'departamento', None) or '')
    cod_regimen = getattr(config, 'codigo_regimen', None) or 'O-13'
    prefijo = getattr(config, 'prefijo_facturacion', None) or 'FACT'
    software_id = getattr(config, 'software_id', None) or ''
    software_pin = getattr(config, 'software_pin', None) or ''
    num_resolucion = getattr(config, 'numero_resolucion', None) or (config.resolucion_dian or '')
    tipo_persona = getattr(config, 'tipo_persona', None) or 'juridica'
    add_account_id = '1' if tipo_persona == 'juridica' else '2'
    iva_pct = float(config.iva_porcentaje or 19)

    # Datos receptor
    tipo_doc_cliente = getattr(factura, 'cliente_tipo_documento', 'CC') or 'CC'
    _TIPOS_DOC = {'CC': '13', 'NIT': '31', 'CE': '22', 'PP': '41',
                  'TI': '12', 'RC': '11', 'TE': '14', 'IE': '21'}
    tipo_doc_dian = _TIPOS_DOC.get(tipo_doc_cliente, '13')
    doc_cliente = factura.cliente_documento or '222222222222'
    nombre_cliente = _escape_xml(factura.cliente_nombre or 'CONSUMIDOR FINAL')
    email_cliente = _escape_xml(getattr(factura, 'cliente_email', '') or '')
    dir_cliente = _escape_xml(getattr(factura, 'cliente_direccion', '') or '')
    ciudad_cliente = _escape_xml(getattr(factura, 'cliente_ciudad', '') or '')

    # Totales
    subtotal = float(factura.subtotal or 0)
    iva_total = float(factura.iva or 0)
    total = float(factura.total or 0)

    # Método de pago → código DIAN
    _METODOS = {'efectivo': '10', 'tarjeta': '48', 'transferencia': '42',
                'mixto': '10', 'credito': '1'}
    cod_pago = _METODOS.get(factura.metodo_pago or 'efectivo', '10')

    # URL verificación DIAN
    if tipo_ambiente == '1':
        url_qr = f"https://catalogo-vpfe.dian.gov.co/document/searchqr?documentkey={cufe}"
    else:
        url_qr = f"https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentkey={cufe}"

    notas = valor_en_letras(total)

    # Líneas de items
    lineas_xml = ''
    for i, item in enumerate(items, 1):
        desc = _escape_xml(item.get('descripcion', 'Producto'))
        cant = float(item.get('cantidad', 1))
        precio = float(item.get('precio_unitario', 0))
        sub = float(item.get('subtotal', precio * cant))
        i_pct = float(item.get('iva_porcentaje', 0))
        i_val = float(item.get('iva_valor', 0))

        lineas_xml += f"""
    <cac:InvoiceLine>
        <cbc:ID>{i}</cbc:ID>
        <cbc:InvoicedQuantity unitCode="94">{cant:.2f}</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="COP">{sub:.2f}</cbc:LineExtensionAmount>
        <cac:TaxTotal>
            <cbc:TaxAmount currencyID="COP">{i_val:.2f}</cbc:TaxAmount>
            <cac:TaxSubtotal>
                <cbc:TaxableAmount currencyID="COP">{sub:.2f}</cbc:TaxableAmount>
                <cbc:TaxAmount currencyID="COP">{i_val:.2f}</cbc:TaxAmount>
                <cac:TaxCategory>
                    <cbc:Percent>{i_pct:.2f}</cbc:Percent>
                    <cac:TaxScheme>
                        <cbc:ID>01</cbc:ID>
                        <cbc:Name>IVA</cbc:Name>
                    </cac:TaxScheme>
                </cac:TaxCategory>
            </cac:TaxSubtotal>
        </cac:TaxTotal>
        <cac:Item>
            <cbc:Description>{desc}</cbc:Description>
            <cac:SellersItemIdentification>
                <cbc:ID>{i}</cbc:ID>
            </cac:SellersItemIdentification>
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="COP">{precio:.2f}</cbc:PriceAmount>
            <cbc:BaseQuantity unitCode="94">1.00</cbc:BaseQuantity>
        </cac:Price>
    </cac:InvoiceLine>"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
    xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
    xmlns:sts="dian:gov:co:facturaelectronica:Structures-2-1"
    xmlns:xades="http://uri.etsi.org/01903/v1.3.2#"
    xmlns:xades141="http://uri.etsi.org/01903/v1.4.1#"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2
        http://docs.oasis-open.org/ubl/os-UBL-2.1/xsd/maindoc/UBL-Invoice-2.1.xsd">
    <ext:UBLExtensions>
        <ext:UBLExtension>
            <ext:ExtensionContent>
                <sts:DianExtensions>
                    <sts:InvoiceControl>
                        <sts:InvoiceAuthorization>{_escape_xml(num_resolucion)}</sts:InvoiceAuthorization>
                        <sts:AuthorizationPeriod>
                            <cbc:StartDate>{fecha_str}</cbc:StartDate>
                            <cbc:EndDate>{fecha_str}</cbc:EndDate>
                        </sts:AuthorizationPeriod>
                        <sts:AuthorizedInvoices>
                            <sts:Prefix>{_escape_xml(prefijo)}</sts:Prefix>
                            <sts:From>1</sts:From>
                            <sts:To>99999999</sts:To>
                        </sts:AuthorizedInvoices>
                    </sts:InvoiceControl>
                    <sts:InvoiceSource>
                        <cbc:IdentificationCode listAgencyID="6"
                            listAgencyName="United Nations Economic Commission for Europe"
                            listSchemeURI="urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.1">CO</cbc:IdentificationCode>
                    </sts:InvoiceSource>
                    <sts:SoftwareProvider>
                        <sts:ProviderID schemeAgencyID="195"
                            schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)">{nit_emisor}</sts:ProviderID>
                        <sts:SoftwareID schemeAgencyID="195"
                            schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)">{_escape_xml(software_id)}</sts:SoftwareID>
                    </sts:SoftwareProvider>
                    <sts:SoftwareSecurityCode schemeAgencyID="195"
                        schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)">{_escape_xml(software_pin)}</sts:SoftwareSecurityCode>
                    <sts:AuthorizationProvider>
                        <sts:AuthorizationProviderID schemeAgencyID="195"
                            schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)"
                            schemeID="4" schemeName="31">800197268</sts:AuthorizationProviderID>
                    </sts:AuthorizationProvider>
                    <sts:QRCode>{url_qr}</sts:QRCode>
                </sts:DianExtensions>
            </ext:ExtensionContent>
        </ext:UBLExtension>
        <ext:UBLExtension>
            <ext:ExtensionContent/>
        </ext:UBLExtension>
    </ext:UBLExtensions>
    <cbc:UBLVersionID>UBL 2.1</cbc:UBLVersionID>
    <cbc:CustomizationID>10</cbc:CustomizationID>
    <cbc:ProfileID>DIAN 2.1</cbc:ProfileID>
    <cbc:ProfileExecutionID>{tipo_ambiente}</cbc:ProfileExecutionID>
    <cbc:ID>{_escape_xml(factura.numero_consecutivo)}</cbc:ID>
    <cbc:UUID schemeID="{tipo_ambiente}" schemeName="CUFE-SHA384">{cufe}</cbc:UUID>
    <cbc:IssueDate>{fecha_str}</cbc:IssueDate>
    <cbc:IssueTime>{hora_str}</cbc:IssueTime>
    <cbc:InvoiceTypeCode listAgencyID="195"
        listAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)"
        listSchemeURI="http://www.dian.gov.co/contratos/facturaelectronica/v1/InvoiceType">01</cbc:InvoiceTypeCode>
    <cbc:Note>{_escape_xml(notas)}</cbc:Note>
    <cbc:DocumentCurrencyCode listID="ISO 4217 Alpha" listAgencyID="6"
        listAgencyName="United Nations Economic Commission for Europe">COP</cbc:DocumentCurrencyCode>
    <cbc:LineCountNumeric>{len(items)}</cbc:LineCountNumeric>
    <cac:OrderReference>
        <cbc:ID>0</cbc:ID>
    </cac:OrderReference>
    <cac:AccountingSupplierParty>
        <cbc:AdditionalAccountID>{add_account_id}</cbc:AdditionalAccountID>
        <cac:Party>
            <cac:PartyName>
                <cbc:Name>{nombre_emisor}</cbc:Name>
            </cac:PartyName>
            <cac:PhysicalLocation>
                <cac:Address>
                    <cbc:Department>{dpto}</cbc:Department>
                    <cbc:CitySubdivisionName/>
                    <cbc:CityName>{ciudad_nombre}</cbc:CityName>
                    <cbc:Line>{dir_emisor}</cbc:Line>
                    <cac:Country>
                        <cbc:IdentificationCode>CO</cbc:IdentificationCode>
                        <cbc:Name languageID="es">Colombia</cbc:Name>
                    </cac:Country>
                </cac:Address>
            </cac:PhysicalLocation>
            <cac:PartyTaxScheme>
                <cbc:RegistrationName>{nombre_emisor}</cbc:RegistrationName>
                <cbc:CompanyID schemeAgencyID="195"
                    schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)"
                    schemeID="{dv_emisor}" schemeName="31">{nit_emisor}</cbc:CompanyID>
                <cbc:TaxLevelCode listName="48">{cod_regimen}</cbc:TaxLevelCode>
                <cac:RegistrationAddress>
                    <cbc:CityName>{ciudad_nombre}</cbc:CityName>
                    <cbc:Line>{dir_emisor}</cbc:Line>
                    <cac:Country>
                        <cbc:IdentificationCode>CO</cbc:IdentificationCode>
                        <cbc:Name languageID="es">Colombia</cbc:Name>
                    </cac:Country>
                </cac:RegistrationAddress>
                <cac:TaxScheme>
                    <cbc:ID>01</cbc:ID>
                    <cbc:Name>IVA</cbc:Name>
                </cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>{nombre_emisor}</cbc:RegistrationName>
                <cbc:CompanyID schemeAgencyID="195"
                    schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)"
                    schemeID="{dv_emisor}" schemeName="31">{nit_emisor}</cbc:CompanyID>
                <cac:CorporateRegistrationScheme>
                    <cbc:ID>{_escape_xml(prefijo)}</cbc:ID>
                </cac:CorporateRegistrationScheme>
            </cac:PartyLegalEntity>
            <cac:Contact>
                <cbc:ElectronicMail>{_escape_xml(config.email or '')}</cbc:ElectronicMail>
            </cac:Contact>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cbc:AdditionalAccountID>1</cbc:AdditionalAccountID>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeAgencyID="195"
                    schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)"
                    schemeID="{tipo_doc_dian}" schemeName="{tipo_doc_cliente}">{doc_cliente}</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyName>
                <cbc:Name>{nombre_cliente}</cbc:Name>
            </cac:PartyName>
            <cac:PhysicalLocation>
                <cac:Address>
                    <cbc:CityName>{ciudad_cliente}</cbc:CityName>
                    <cbc:Line>{dir_cliente}</cbc:Line>
                    <cac:Country>
                        <cbc:IdentificationCode>CO</cbc:IdentificationCode>
                        <cbc:Name languageID="es">Colombia</cbc:Name>
                    </cac:Country>
                </cac:Address>
            </cac:PhysicalLocation>
            <cac:PartyTaxScheme>
                <cbc:RegistrationName>{nombre_cliente}</cbc:RegistrationName>
                <cbc:CompanyID schemeAgencyID="195"
                    schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)"
                    schemeID="0" schemeName="{tipo_doc_cliente}">{doc_cliente}</cbc:CompanyID>
                <cbc:TaxLevelCode listName="48">R-99-PN</cbc:TaxLevelCode>
                <cac:TaxScheme>
                    <cbc:ID>ZZ</cbc:ID>
                    <cbc:Name>No aplica</cbc:Name>
                </cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>{nombre_cliente}</cbc:RegistrationName>
                <cbc:CompanyID schemeAgencyID="195"
                    schemeAgencyName="CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)"
                    schemeID="0" schemeName="{tipo_doc_cliente}">{doc_cliente}</cbc:CompanyID>
            </cac:PartyLegalEntity>
            <cac:Contact>
                <cbc:ElectronicMail>{email_cliente}</cbc:ElectronicMail>
            </cac:Contact>
        </cac:Party>
    </cac:AccountingCustomerParty>
    <cac:PaymentMeans>
        <cbc:ID>{cod_pago}</cbc:ID>
        <cbc:PaymentMeansCode>{cod_pago}</cbc:PaymentMeansCode>
        <cbc:PaymentDueDate>{fecha_str}</cbc:PaymentDueDate>
        <cbc:PaymentID>{_escape_xml((factura.metodo_pago or 'efectivo').upper())}</cbc:PaymentID>
    </cac:PaymentMeans>
    <cac:TaxTotal>
        <cbc:TaxAmount currencyID="COP">{iva_total:.2f}</cbc:TaxAmount>
        <cac:TaxSubtotal>
            <cbc:TaxableAmount currencyID="COP">{subtotal:.2f}</cbc:TaxableAmount>
            <cbc:TaxAmount currencyID="COP">{iva_total:.2f}</cbc:TaxAmount>
            <cac:TaxCategory>
                <cbc:Percent>{iva_pct:.2f}</cbc:Percent>
                <cac:TaxScheme>
                    <cbc:ID>01</cbc:ID>
                    <cbc:Name>IVA</cbc:Name>
                </cac:TaxScheme>
            </cac:TaxCategory>
        </cac:TaxSubtotal>
    </cac:TaxTotal>
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount currencyID="COP">{subtotal:.2f}</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount currencyID="COP">{subtotal:.2f}</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="COP">{total:.2f}</cbc:TaxInclusiveAmount>
        <cbc:AllowanceTotalAmount currencyID="COP">0.00</cbc:AllowanceTotalAmount>
        <cbc:ChargeTotalAmount currencyID="COP">0.00</cbc:ChargeTotalAmount>
        <cbc:PrePaidAmount currencyID="COP">0.00</cbc:PrePaidAmount>
        <cbc:PayableAmount currencyID="COP">{total:.2f}</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
    {lineas_xml}
</Invoice>"""

    return xml


# ---------------------------------------------------------------------------
# Código QR
# ---------------------------------------------------------------------------

def generar_qr_base64(url):
    """
    Genera imagen QR como base64 PNG.
    Requiere: pip install qrcode[pil]
    Retorna None si la librería no está disponible.
    """
    try:
        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except ImportError:
        return None


def url_verificacion_dian(cufe, tipo_ambiente="2"):
    """URL de consulta en el portal DIAN."""
    if tipo_ambiente == '1':
        return f"https://catalogo-vpfe.dian.gov.co/document/searchqr?documentkey={cufe}"
    return f"https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentkey={cufe}"
