# -*- coding: utf-8 -*-

import openerp.addons.web.http as http
from openerp.addons.web.controllers.main import Binary
from openerp import exceptions
from openerp.http import request
import base64
import simplejson
import suds
import urllib2
from suds.client import Client
from datetime import datetime


class MyBinary(Binary):

    _url_maarch = ''
    _user_maarch = ''
    _password_maarch = ''
    _filesubject_in_maarch = ''

    @http.route()
    def upload_attachment(self, callback, model, id, ufile):
        """
        Check if the Maarch server configuration is OK and call the _add_to_maarch method.
        Display an appropriate message if the document can't be added into Maarch.
        :param callback
        :param model : model name
        :param id
        :param ufile : file that has to be added into Odoo and Maarch
        """
        out = """<script language="javascript" type="text/javascript">
                    var win = window.top.window;
                    win.jQuery(win).trigger(%s, %s);
                </script>"""

        if self.get_the_active_conf().get('is_conf_active'):
            try:
                if not self._filesubject_in_maarch:
                    # if the user hasn't mentionned any subject we use the filename
                    if self._filesubject_in_maarch == "":
                        self._filesubject_in_maarch = ufile.filename
                    # if the user has clicked on "cancel" we abort the process
                    else:
                        args = {'error': "La pièce jointe n'a pas été enregistrée dans Maarch ni dans Odoo.",
                                'maarchError': True}
                        return out % (simplejson.dumps(callback), simplejson.dumps(args))
                self._add_to_maarch(base64.encodestring(ufile.read()), self._filesubject_in_maarch)
            except exceptions.ValidationError as e:
                args = {'error': str(e[1]), 'maarchError': True}
                return out % (simplejson.dumps(callback), simplejson.dumps(args))
            # get back to the beginning of the file
            ufile.seek(0)
        return super(MyBinary, self).upload_attachment(callback, model, id, ufile)

    @http.route('/tempo/maarchconnector/get_the_active_conf', type='json', auth='user')
    def get_the_active_conf(self):
        """
        Indicate if a Maarch configuration is active. If so, get the corresponding datas.
        """
        configuration_model = request.registry["maarchconnector.configuration"]
        active_conf = configuration_model.get_the_active_configuration(request.cr, request.uid, [])
        is_conf_active = False
        if active_conf:
            self._url_maarch = '%s/ws_server.php?WSDL' % active_conf.server_address
            self._user_maarch = active_conf.maarch_user_login
            self._password_maarch = active_conf.maarch_user_password
            is_conf_active = True
        return {'is_conf_active': is_conf_active}

    @http.route('/tempo/maarchconnector/set_subject', type='json', auth='none')
    def set_subject(self, subject):
        """
        Set the subject for the file to be registered in Maarch
        :param subject:
        :return:
        """
        self._filesubject_in_maarch = subject
        #return {}


    def _add_to_maarch(self, base64_encoded_content, document_subject):
        """
        Add the file into Maarch under the name "document_subject"
        :param base64_encoded_content: content of the file encoded in base 64
        :param document_subject: file name or subject
        :return:
        """
        try:
            _client_maarch = Client(self._url_maarch, username=self._user_maarch, password=self._password_maarch)
            error = ''
            mydate = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # data relative to the document
            data = _client_maarch.factory.create('arrayOfData')
            typist = _client_maarch.factory.create('arrayOfDataContent')
            typist.column = 'typist'
            typist.value = 'odoo'
            typist.type = 'string'
            doc_date = _client_maarch.factory.create('arrayOfDataContent')
            doc_date.column = 'doc_date'
            doc_date.value = mydate
            doc_date.type = 'string'
            type_id = _client_maarch.factory.create('arrayOfDataContent')
            type_id.column = 'type_id'
            type_id.value = '15'  # misc. by default
            type_id.type = 'string'
            subject = _client_maarch.factory.create('arrayOfDataContent')
            subject.column = 'subject'
            subject.value = document_subject.decode('utf8')
            subject.type = 'string'
            data.datas.append(typist)
            data.datas.append(doc_date)
            data.datas.append(type_id)
            data.datas.append(subject)
            # call to the web service method
            _client_maarch.service.storeResource(base64_encoded_content, data, 'letterbox_coll',
                                                 'res_letterbox', 'pdf', 'INIT')
        except urllib2.URLError:
            error = "accès au serveur impossible.<br/>L'adresse fournie est incorrecte, ou le serveur est indisponible."
        except suds.transport.TransportError:
            error = "connexion impossible.<br/>Vérifiez l'URL et les identifiants de connexion fournis."
        except Exception:
            error = "une erreur est survenue lors du traitement."
        if error:
            raise exceptions.ValidationError("La pièce jointe ne peut pas être enregistrée dans Maarch&nbsp: %s" % error)

