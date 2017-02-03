/*
 * Copyright (c) 2015-2017 The Khronos Group Inc.
 * Copyright (c) 2015-2017 Valve Corporation
 * Copyright (c) 2015-2017 LunarG, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * Author: Mark Lobodzinski <mark@lunarg.com>
 * Author: Mark Young <marky@lunarg.com>
 *
 */

#pragma once

// Extension interception for vkGetInstanceProcAddr function, so we can return
// the appropriate information for any instance extensions we know about.
bool extension_instance_gpa(struct loader_instance *ptr_instance, const char *name, void **addr);

// Extension interception for vkCreateInstance function, so we can properly
// detect and enable any instance extension information for extensions we know
// about.
void extensions_create_instance(struct loader_instance *ptr_instance, const VkInstanceCreateInfo *pCreateInfo);

// Extension interception for vkGetDeviceProcAddr function, so we can return
// an appropriate terminator if this is one of those few device commands requiring
// a terminator.
PFN_vkVoidFunction get_extension_device_proc_terminator(const char *pName);

// Dispatch table properly filled in with appropriate terminators for the
// supported extensions.
extern const VkLayerInstanceDispatchTable instance_disp;

// Array of extension strings for instance extensions we support.
extern const char *const LOADER_INSTANCE_EXTENSIONS[];
