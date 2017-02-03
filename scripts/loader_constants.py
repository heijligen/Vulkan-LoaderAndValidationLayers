#!/usr/bin/python3 -i
#
# Copyright (c) 2015-2017 The Khronos Group Inc.
# Copyright (c) 2015-2017 Valve Corporation
# Copyright (c) 2015-2017 LunarG, Inc.
# Copyright (c) 2015-2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Mark Young <marky@lunarg.com>

WSI_EXT_NAMES = ['VK_KHR_surface',
                 'VK_KHR_display',
                 'VK_KHR_xlib_surface',
                 'VK_KHR_xcb_surface',
                 'VK_KHR_wayland_surface',
                 'VK_KHR_mir_surface',
                 'VK_KHR_win32_surface',
                 'VK_KHR_android_surface',
                 'VK_KHR_swapchain',
                 'VK_KHR_display_swapchain']

AVOID_EXT_NAMES = ['VK_EXT_debug_report']

DEVICE_CMDS_NEED_TERM = ['vkGetDeviceProcAddr',
                         'vkCreateSwapchainKHR',
                         'vkCreateSharedSwapchainsKHR',
                         'vkDebugMarkerSetObjectTagEXT',
                         'vkDebugMarkerSetObjectNameEXT']

def IsCommandExtension(command_name) :
    if ('KHR' in command_name or 'KHX' in command_name or
        'EXT' in command_name or 'AMD' in command_name or
        'ARM' in command_name or 'GOOGLE' in command_name or
        'LUNARG' in command_name or 'NN' in command_name or
        'NV' in command_name):
        return True
    else:
        return False
