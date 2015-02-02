#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File          : tinker_start.py
# Module        : tinker
# Author        : bss
# Creation date : 2015-02-01
#  Last modified: 2015-02-02, 10:48:03
# Description   : Startup script for tinker, main body.
#

import sys
import os
import rospy
import ConfigParser
import getopt
from std_msgs.msg import String
from d_say.srv import *
import subprocess

class Starter:
    def __init__(self):
        self.config = ConfigParser.SafeConfigParser(
                {'xdotool_sleep_time': '4'}
        )
        self.cwd = os.path.split(os.path.realpath(__file__))[0];
        self.gets_str = ''
        self.isRemote = False
        self.tabNum = 0

    def d_say_IsPlaying(self):
        rospy.wait_for_service('/say/IsPlaying')
        try:
            func_IsPlaying = rospy.ServiceProxy('/say/IsPlaying', IsPlaying)
            resp = func_IsPlaying()
            return resp.playing
        except rospy.ServiceException, e:
            print('fail: %s'%e)
            return False

    def Speak(self, text):
        print('speak: "' + text + '"')
        if self.d_say_IsPlaying():
            print('waiting for d_say...')
            while (not rospy.is_shutdown()) and self.d_say_IsPlaying():
                self.rate.sleep()
        self.say_pub.publish(str(text))
        self.rate.sleep()

    def Wait(self):     # wait for C-c
        while not rospy.is_shutdown():
            self.rate.sleep()

    def StartNewTab(self, cmd):
        self.tabNum += 1
        if self.isRemote:
            logfile = self.cwd + '/../../' \
                    + 'share/start/log' + str(self.tabNum) + '.log'
            command = cmd + ' > ' + logfile
            print('Run sh: %s: log to %s' % (cmd, logfile))
            os.system(command + ' & ')
            sys.stdout.flush()
        else:
            t = self.config.get('scripts', 'xdotool_sleep_time')
            os.system('xdotool key ctrl+shift+t ; sleep ' + str(t) + ' ; '
                    + 'xdotool type "' + cmd + '" ; xdotool key "Return"')

    def SwitchBack(self):   # switch back to this tab
        if not self.isRemote:
            os.system('xdotool key alt+1 ; sleep 1')

    def RunFile(self, filename):      # run tinkerstart script
        print('run ' + filename + '.tinkerstart')
        filepath = self.cwd + '/scripts/' + filename + '.tinkerstart'
        try:
            f = open(filepath, 'r')
            lines = f.readlines()
        except Exception, e:
            print('Error: cannot open %s.tinkerstart: %s'
                    % (filename, e))
            return
        self.RunLines(lines, filename, 0)

    # run script in memory
    def RunLines(self, lines, filename, linenumber):
        nesting_level = 0
        nesting_type = ''
        values = []
        count = 0
        linenumberOfNesting = 0
        for originLine in lines:
            count += 1
            handled = False
            line = originLine.strip()
            line = line.replace('$(str)', self.gets_str)
            if (line.startswith('#') or line == ''):
                continue
            if line == 'end':
                nesting_level -= 1
                if nesting_level < 0:
                    self.RaiseError(filename, count, originLine.strip('\n'),
                            'SyntaxError: found an unexcepted "end".')
                    break
                if nesting_level == 0:
                    if nesting_type == 'switch':
                        self.HandleSwitch(values, filename,
                                linenumberOfNesting)
                        values = []
                handled = True
            if nesting_level > 0:
                values.append(line)
                continue
            if line.startswith('print'):
                print('print: ' + line[len('print'):].strip())
                continue
            if line.startswith('speak'):
                value = line[len('speak'):].strip()
                value = self.RemoveQuotes(value)
                self.Speak(value)
                continue
            if line == 'switch':
                nesting_level += 1
                if nesting_level == 1:
                    nesting_type = 'switch'
                    values = []
                    linenumberOfNesting = count
                continue
            if line == 'gets':
                try:
                    # I hope it will work on python 2 and 3
                    self.gets_str = sys.stdin.readline().strip('\n')
                except Exception, e:
                    print('Warning: in gets: %s'%e)
                    self.gets_str = ''
                continue
            if line.startswith('system'):
                os.system(line[len('system'):].strip())
                continue
            if line.startswith('ros'):
                self.StartNewTab(line)
                continue
            if line.startswith('exec'):
                value = self.RemoveQuotes(line[len('exec'):].strip())
                try:
                    self.RunFile(value)
                except Exception, e:
                    print('Error: In file ' + value + '. Exec in '
                            + filename + ': ' + str(count) + ': %s'%e)
                continue 
            if line.startswith('case'):
                self.RaiseError(filename, count, originLine.strip('\n'),
                        'SyntaxError: found an unexcepted "case".')
                break
            if line.startswith('break'):
                self.RaiseError(filename, count, originLine.strip('\n'),
                        'SyntaxError: found an unexcepted "break".')
                break
            if not handled:
                self.RaiseError(filename, count, originLine.strip('\n'),
                        'SyntaxError: unable to understand this line.')
                break

    # run scripts between switch & end
    def HandleSwitch(self, lines, filename, linenumber):
        count = linenumber
        cases = []
        nesting_level = 0
        # traversal all cases
        for originLine in lines:
            count += 1
            line = originLine.strip()
            if line.startswith('case'):
                nesting_level += 1
                if nesting_level == 1:
                    cases.append(self.RemoveQuotes(
                            line[len('case'):].strip()))
                    continue
            if line.startswith('break'):
                nesting_level -= 1
                if nesting_level < 0:
                    self.RaiseError(filename, count, originLine.strip('\n'),
                            'SyntaxError: found an unexcepted "break".')
                    break

        self.SwitchBack()
        # select a case by keyboard (or voice?)
        sel = self.SelectACase(cases)
        self.HandleCase(lines, cases[sel-1], filename, linenumber)

    def HandleCase(self, lines, theCase, filename, linenumber):
        count = linenumber
        values = []
        nesting_level = 0
        linenumberOfNesting = 0
        found = False
        for originLine in lines:
            count += 1
            line = originLine.strip()
            if line.startswith('break'):
                nesting_level -= 1
                if nesting_level < 0:
                    self.RaiseError(filename, count, originLine.strip('\n'),
                            'SyntaxError: found an unexcepted "break".')
                    break
                if nesting_level == 0 and found:
                    self.RunLines(values, filename, linenumberOfNesting)
                    break
                continue
            if found:
                values.append(originLine)
            if line.startswith('case'):
                nesting_level += 1
                case = self.RemoveQuotes(line[len('case'):].strip())
                if (nesting_level) == 1 and (case == theCase):
                    found = True
                    linenumberOfNesting = count
                continue

    def SelectACase(self, cases):
        menu = 'Please select:'
        count = 0
        for case in cases:
            count += 1
            menu += ' %d.(%s)' % (count, case)
        sel = 0
        while (not rospy.is_shutdown()) and (sel == 0):
            print(menu)
            try:
                sel = int(input())
            except:
                print('Error: invalid input.')
                continue
            if sel <= 0 or sel > count:
                print('Error: input out of range.')
                sel = 0
        return sel

    def RaiseError(self, filename, linenumber, line, desc):
        print(filename + ':' + str(linenumber) + ': ' + line)
        print('Error: ' + desc)
        raise Exception(desc)

    def RemoveQuotes(self, value):
        if value.startswith('"') and value.startswith('"'):
            value = value[1:-1]
        return value

    def GetOpts(self, argv):
        try:
            opts, argv = getopt.getopt(argv[1:], 'h', ['help', 'remote'])
        except getopt.GetoptError, e:
            print('Error: invalid argv: %s'%e)
            sys.exit(2)
        except Exception, e:
            print('Error: %s'%e)
            sys.exit(1)
        
        for o, a in opts:
            if o in ('-h', '--help'):
                print('https://github.com/tinkerfuroc/tinker2014')
                sys.exit(0)
            if o in ('--remote'):
                self.isRemote = True


    def Start(self, argv):
        print(self.cwd)
        # config
        self.config.read(self.cwd + '/settings.ini')
        # opts
        self.GetOpts(argv)

        self.StartNewTab('roscore')
        rospy.init_node('tinker_start', anonymous=True)
        self.StartNewTab('rosrun d_say say_node.py')
        self.say_pub = rospy.Publisher(
                '/say/sentence', String, queue_size=1)

        self.SwitchBack()
        self.rate = rospy.Rate(10)
        try:
            self.RunFile('main')
        except Exception, e:
            print('Error: In file main.tinkerstart: %s'%e)
        print('Press C-c to exit...')
        self.Wait()
        
def main(argv):
    starter = Starter()
    starter.Start(argv)
    print('Bye!')

if __name__ == '__main__':
    main(sys.argv)
