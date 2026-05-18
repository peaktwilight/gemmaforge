    def handle_message(self, ch, method, properties, body):
        """
        this is a pika.basic_consumer callback
        handles client inputs, runs appropriate workflows and views

        Args:
            ch: amqp channel
            method: amqp method
            properties:
            body: message body
        """
        input = {}
        try:
            self.sessid = method.routing_key

            input = json_decode(body)
            data = input['data']

            # since this comes as "path" we dont know if it's view or workflow yet
            #TODO: just a workaround till we modify ui to
            if 'path' in data:
                if data['path'] in settings.VIEW_URLS:
                    data['view'] = data['path']
                else:
                    data['wf'] = data['path']
            session = Session(self.sessid)

            headers = {'remote_ip': input['_zops_remote_ip']}

            if 'wf' in data:
                output = self._handle_workflow(session, data, headers)
            elif 'job' in data:

                self._handle_job(session, data, headers)
                return
            else:
                output = self._handle_view(session, data, headers)

        except HTTPError as e:
            import sys
            if hasattr(sys, '_called_from_test'):
                raise
            output = {'cmd': 'error', 'error': self._prepare_error_msg(e.message), "code": e.code}
            log.exception("Http error occurred")
        except:
            self.current = Current(session=session, input=data)
            self.current.headers = headers
            import sys
            if hasattr(sys, '_called_from_test'):
                raise
            err = traceback.format_exc()
            output = {'error': self._prepare_error_msg(err), "code": 500}
            log.exception("Worker error occurred with messsage body:\n%s" % body)
        if 'callbackID' in input:
            output['callbackID'] = input['callbackID']
        log.info("OUTPUT for %s: %s" % (self.sessid, output))
        output['reply_timestamp'] = time()
        self.send_output(output)
