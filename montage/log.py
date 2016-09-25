
import os

from lithoxyl import (Logger,
                      StreamEmitter,
                      SensibleSink,
                      SensibleFilter,
                      SensibleFormatter)

from lithoxyl.sinks import DevDebugSink

# import lithoxyl; lithoxyl.get_context().enable_async()

script_log = Logger('dev_script')

fmt = ('{status_char}+{import_delta_s}'
       ' - {duration_ms:>8.3f}ms'
       ' - {parent_depth_indent}{end_message}')

begin_fmt = ('{status_char}+{import_delta_s}'
             ' --------------'
             ' {parent_depth_indent}{begin_message}')

stderr_fmtr = SensibleFormatter(fmt,
                                begin=begin_fmt)
stderr_emtr = StreamEmitter('stderr')
stderr_filter = SensibleFilter(success='info',
                               failure='debug',
                               exception='debug')
stderr_sink = SensibleSink(formatter=stderr_fmtr,
                           emitter=stderr_emtr,
                           filters=[stderr_filter])
script_log.add_sink(stderr_sink)

dds = DevDebugSink(post_mortem=bool(os.getenv('ENABLE_PDB')))
script_log.add_sink(dds)
