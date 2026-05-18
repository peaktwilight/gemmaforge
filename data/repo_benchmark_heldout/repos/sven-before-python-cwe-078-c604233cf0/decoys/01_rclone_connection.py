    def _formatCredentials(self, data, name):
        """
        Credentials are of the form
        RCLONE_CONFIG_CURRENT_TYPE=s3
            ^          ^        ^   ^
        [mandatory  ][name  ][key][value]
        """

        prefix = "RCLONE_CONFIG_{}".format(name.upper())

        credentials = {}
        credentials['{}_TYPE'.format(prefix)] = data.type

        def _addCredential(credentials, env_key, data_key):
            value = getattr(data, data_key, None)
            if value is not None:
                credentials[env_key] = value
            return credentials


        if data.type == 's3':
            credentials = _addCredential(credentials,
                '{}_REGION'.format(prefix),
                's3_region'
            )
            credentials = _addCredential(credentials,
                '{}_ACCESS_KEY_ID'.format(prefix),
                's3_access_key_id'
            )
            credentials = _addCredential(credentials,
                '{}_SECRET_ACCESS_KEY'.format(prefix),
                's3_secret_access_key'
            )

            credentials = _addCredential(credentials,
                '{}_ENDPOINT'.format(prefix),
                's3_endpoint'
            )
            credentials = _addCredential(credentials,
                '{}_V2_AUTH'.format(prefix),
                's3_v2_auth'
            )

        elif data.type == 'azureblob':
            credentials = _addCredential(credentials,
                '{}_ACCOUNT'.format(prefix),
                'azure_account'
            )
            credentials = _addCredential(credentials,
                '{}_KEY'.format(prefix),
                'azure_key'
            )

        elif data.type == 'swift':
            credentials = _addCredential(credentials,
                '{}_USER'.format(prefix),
                'swift_user'
            )
            credentials = _addCredential(credentials,
                '{}_KEY'.format(prefix),
                'swift_key'
            )
            credentials = _addCredential(credentials,
                '{}_AUTH'.format(prefix),
                'swift_auth'
            )
            credentials = _addCredential(credentials,
                '{}_TENANT'.format(prefix),
                'swift_tenant'
            )

        elif data.type == 'google cloud storage':
            credentials = _addCredential(credentials,
                '{}_CLIENT_ID'.format(prefix),
                'gcp_client_id'
            )
            credentials = _addCredential(credentials,
                '{}_SERVICE_ACCOUNT_CREDENTIALS'.format(prefix),
                'gcp_service_account_credentials'
            )
            credentials = _addCredential(credentials,
                '{}_PROJECT_NUMBER'.format(prefix),
                'gcp_project_number'
            )
            credentials = _addCredential(credentials,
                '{}_OBJECT_ACL'.format(prefix),
                'gcp_object_acl'
            )
            credentials = _addCredential(credentials,
                '{}_BUCKET_ACL'.format(prefix),
                'gcp_bucket_acl'
            )

        else:
            logging.error("Connection type unknown: {}".format(data.type))

        return credentials
