#!/usr/bin/env python3
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saleor.settings")
     # start new section
    from django.conf import settings
    print('test!')

    if settings.DEBUG:
        print('test!')

        if os.environ.get('RUN_MAIN') or os.environ.get('WERKZEUG_RUN_MAIN'):
            import ptvsd

            ptvsd.enable_attach(address=('0.0.0.0', 3000))
            print('Attached!')
    # end new section

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
