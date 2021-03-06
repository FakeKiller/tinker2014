#!/usr/bin/env python
# -*- coding: utf-8 -*-
# file: init.py
# created by bss at 2014-05-09
# Last modified: 2015-02-02, 17:16:44
# 初始化一组语音识别的任务
#

import sys
import os
import getopt
import rospkg

def Usage():
    print('init.py usage:')
    print('初始化一组语音识别任务，处理${task}/sent.txt,gram.jsgf')
    print('-h,--help: print help message.')
    print('--init: init a dir for your task')
    print('-t,--task: input the name of the task.')
    print('')
    print('example:')
    print('python init.py --init whoiswho')
    print('python init.py -t whoiswho')

def main(argv):
    if len(argv) <= 1:
        Usage()
        sys.exit(2)
    try:
        opts, args = getopt.getopt(argv[1:], 'ht:',
                ['help', 'task=', 'init='])
    except getopt.GetoptError, err:
        print(str(err))
        Usage()
        sys.exit(2)
    except:
        Usage()
        sys.exit(1)

    for o, a in opts:
        if o in ('-h', '--help'):
            Usage()
            sys.exit(0)
        elif o in ('--init'):
            initDir(a)
            sys.exit(0)
        elif o in ('-t', '--task'):
            processTask(a)
            sys.exit(0)

def initDir(task):
    outdir = rospkg.RosPack().get_path('l_sphinx_wrapper') \
            + '/launches'
    taskdir = outdir + '/tasks/' + task
    os.system('mkdir ' + taskdir)
    os.system('touch ' + taskdir + '/sent.txt')
    os.system('touch ' + taskdir + '/gram.jsgf')

    fp = open(taskdir + '/gram.jsgf', 'w')
    fp.write('#JSGF v1.0;\n')
    fp.write('grammar ' + task + ';\n')
    fp.close()

    fp = open(outdir + '/' + task + '.launch', 'w')
    fp.write('<launch>\n')
    fp.write('\n')
    fp.write('  <node name="recognizer" pkg="l_sphinx_wrapper" ' \
            + 'type="recognizer.py" output="screen">\n')
    fp.write('    <param name="fsg" ' \
            + 'value="$(find l_sphinx_wrapper)/launches/tasks/' \
            + task + '/finite_state.fsg"/>\n')
    fp.write('    <param name="dict" ' \
            + 'value="$(find l_sphinx_wrapper)/launches/tasks/'
            + task + '/words.dic"/>\n')
    fp.write('  </node>\n')
    fp.write('\n')
    fp.write('</launch>\n')
    fp.close()

def processTask(task):
    scriptdir = rospkg.RosPack().get_path('l_sphinx_wrapper') \
            + '/../../../ui/l_sphinx_wrapper'
    os.system('python ' + scriptdir + '/input2dict.py -t ' + task)
    os.system('python ' + scriptdir + '/jsgf2fsg.py -t ' + task)
    

if __name__ == '__main__':
    main(sys.argv)
