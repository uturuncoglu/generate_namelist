#!/usr/bin/env python
"""
Parses source files and creates CIME compatible namelist XML file
"""
import re
import os
import sys
import shutil
import subprocess

# function to remove entry
def remove_values_from_list(the_list, val1, val2=None):
    if the_list:
        #if val2 is not None:
        #    return [value.lower().strip() for value in the_list if val1 not in value and val2 not in value]
        #else:
        #    return [value.lower().strip() for value in the_list if val1 not in value]
        return [value.lower().strip() for value in the_list if val1 not in value]
    else:
        return []

# accepted variable types
accepted_variable_types = {'real', 'double', 'integer', 'logical', 'character'}

# accepted arithmetic operations
accepted_arit_opts = {'+', '-', '/', '*'}

# intrinsic functions
int_func = {'max', 'min', 'sum', 'real', 'nint', 'int'}

# list files in the directory
#files = []
#ext_list = ['.F90', '.f90', '.F', '.f']
##for r, d, f in os.walk('/glade/scratch/jedwards/SMS_D.C96.UFS_Weather.cheyenne_intel.20191205_085208_1gpicj/bld/atm/obj/FV3/.'):
#for r, d, f in os.walk('/glade/scratch/jedwards/SMS_D.C96.UFS_Weather.cheyenne_intel.20191205_085208_1gpicj/bld/atm/obj/FMS/.'):
#    for fn in f:
#        if any(x in fn for x in ext_list) and ".o" not in fn:
#            files.append(os.path.join(r, fn))

# exist in two different place and namphysics/physics/gfdl_cloud_microphys.F90 has less namelist variables
# TODO: we might need to create two different namelist definition XML file
#files.remove("./namphysics/physics/gfdl_cloud_microphys.F90")
#files.remove("./ccpp/physics/physics/module_gfdl_cloud_microphys.F90")

# create a folder that has list of files but their pre-processed versions
#path_out = 'fpp/'
#if not os.path.exists(path_out):
#    os.makedirs(path_out)
#else:
#    shutil.rmtree(path_out)
#fv3
#cpp_flags = "-DCCPP -DFV3 -DGFS_PHYS -DINTERNAL_FILE_NML -DLINUX -DMKL -DMOIST_CAPPA -DMPI -DNEMS_GSM -DNETCDF -DNEW_TAUCTMAX -DOPENMP -DSPMD -DSTATIC -DUSE_COND -DUSE_GFSL63 -DUSE_LOG_DIAG_FIELD_INFO -Duse_WRTCOMP -Duse_libMPI -Duse_netCDF" 
#fms
#cpp_flags = "-DGFS_PHYS -DINTERNAL_FILE_NML -DMOIST_CAPPA -DNEW_TAUCTMAX -DSPMD -DUSE_COND -DUSE_GFSL63 -DUSE_LOG_DIAG_FIELD_INFO -Duse_WRTCOMP -Duse_libMPI -Duse_netCDF"
#for f in files:
#    print f, os.path.basename(f).replace('.F90','.i90').replace('.f90','.i90').replace('.F','.i').replace('.f','.i')
#    os.system("ifort -fpp -save-temps {} {} >&/dev/null".format(cpp_flags, f))
#    os.system("mv {} {}".format(os.path.basename(f).replace('.F90','.i90').replace('.f90','.i90').replace('.F','.i').replace('.f','.i'), 'fpp/.'))
#sys.exit()

# list files in the directory
files = []
for r, d, f in os.walk('fpp'):
    for file in f:
        if '.i' in file:
            files.append(os.path.join(r, file))

# remove certain files
files = [x for x in files if '_restart' not in x]
#files = ['fpp/sfcsub.i'] 
#files = ['fpp/oda_core.i90'] 
#files = ['fpp/amip_interp.i90'] 
#files = ['fpp/diag_manager.i90'] 
files = ['fpp/fms_io.i90'] 

# loop over files
nml_list = []
var_dict = {}
for f in files:
    # get namelist groups
    with open(f, 'r') as fin:
        for line in fin.xreadlines():
            regex = r"nml[\s]*="
            match1 = re.search(regex, line)

            regex = r"namelist[\s]*/"
            match2 = re.search(regex, line)

            regex = r"NAMELIST[\s]*/"
            match3 = re.search(regex, line)

            #print match1, match2, match3, line

            match = False
            if (match1 or '=ios' in line) and '_nml' in line and '%' not in line and '::' not in line and '!' not in line:
                if len(line.split(',')) > 1:
                    nml_name = line.split(',')[1].replace('nml=','').replace('nml =','').strip('\n').strip(')').strip()
                    match = True
            elif (match2 or match3) and '!' not in line:
                nml_name = line.split('/')[1].strip()
                match = True

            if match:
                if nml_name not in nml_list:
                    nml_list.append(nml_name)

    # remove fn_nml from the list
    nml_list = [x for x in nml_list if 'fn_nml' not in x]

    # read whole file to list
    f = open(f, 'r')
    lines = [x for x in f.readlines() if x.strip()]
    f.close()
    lines = [x.strip() for x in lines]
    lines = [x for x in lines if not x.startswith('#')]
    lines = [x for x in lines if not x.startswith('!')]

    # find variables belong to namelist groups
    loc = 0
    for line in lines:
        for nml in nml_list:
            if nml in line and 'namelist' in line.lower():
                #print line
                loc_local = loc
                while True:
                    line_local = lines[loc_local].strip().lower()

                    # if there is a comment at the end of the line, just got until that point
                    read_next = False
                    indx = line_local.find('!')
                    if indx != -1:
                        if  indx == 0:
                            read_next = True
                        else:
                            line_local = line_local[:indx-1]

                    # skip line
                    if read_next:
                        loc_local = loc_local+1
                        continue

                    # first line vs. rest
                    if loc_local == loc:
                        var_names = line_local.split('/')[2].split(',')
                    else:
                        var_names = line_local.split(',')

                    var_names = [x.strip(' ') for x in var_names]
                    var_names = [x.strip('\n') for x in var_names]
 
                    # check for continuation line
                    has_and = False
                    var_list_len = len(var_names)
                    #if any('&' in x for x in var_names) :# or not var_names[var_list_len-1]:
                    if any(x.endswith('&') for x in var_names):
                        has_and = True

                    # remove empty string and & symbol from the list
                    var_names = [x.strip('&') for x in var_names]
                    #var_names = remove_values_from_list(var_names, '&')
                    #var_names = remove_values_from_list(var_names, '::')
                    #var_names = remove_values_from_list(var_names, '=')
                    #var_names = remove_values_from_list(var_names, 'subroutine')
                    #var_names = remove_values_from_list(var_names, 'namelist')
                    #var_names = remove_values_from_list(var_names, 'operator')
                    #var_names = remove_values_from_list(var_names, 'only')
                    #var_names = remove_values_from_list(var_names, 'if ')
                    #var_names = remove_values_from_list(var_names, 'use ')

                    # add variables to the list
                    if nml not in var_dict:
                        var_dict.update({ nml : var_names })
                    else:
                        var_dict[nml].extend(var_names)
                    loc_local = loc_local+1

                    #print loc_local, line_local, has_and, var_names, var_list_len

                    # if it has only one line
                    if not has_and: 
                        if nml not in var_dict:
                            var_dict.update({ nml : var_names })
                        break
        loc = loc+1

# sort lists
nml_list.sort()

# sort dictionary and remove duplicates
sorted(var_dict)
for i in nml_list:
    # remove empty and duplicated elements
    var_dict[i] = [x.strip() for x in var_dict[i] if x]
    var_dict[i] = list(set(var_dict[i]))

    # sort
    var_dict[i].sort()

#print nml_list
#for i in nml_list:
#   print i, var_dict[i], len(var_dict[i])
#sys.exit()

# create skeleton of var_meta
var_meta = dict()
for nml in nml_list:
    for var in var_dict[nml]:
        var_meta.setdefault(nml+":"+var, []).append(['None','None','None'])

# search to find dimension, types and defaults
for nml in nml_list:
#for nml in ["gfs_physics_nml"]:
#for nml in ["nam_physics_nml"]:
#for nml in ["coupler_nml"]:
#for nml in ["fv_core_nml"]:
#for nml in ["fv_nwp_nudge_nml"]:
#for nml in ["test_case_nml"]:
#for nml in ["atmos_model_nml"]:
#for nml in ["nest_nml"]:
    for var in var_dict[nml]:
    #for var in ["fscav_aero"]:
    #for var in ["current_date"]:
    #for var in ["knob_ugwp_stoch"]:
    #for var in ["dt_atmos"]:
    #for var in ["layout"]:
    #for var in ["beta"]:
    #for var in ["r_inc"]:
    #for var in ["prautco"]:
    #for var in ["CLEFF"]:
    #for var in ["nestupdate"]:
    #for var in ["disheat"]:
    #for var in ["bubble_do"]:
    #for var in ["alpha"]:
    #for var in ["ccpp_suite"]:
    #for var in ["res_latlon_dynamics"]:
    #for var in ["n_split"]:
    #for var in ["a2b_ord"]:
        # get file with namelist definition
        f1 = subprocess.check_output("grep -l '"+nml+"' fpp/*", shell=True).splitlines()
        nf = len(f1)

        file_str = ""
        for i in f1:
            file_str = file_str+i+" "

            match_global = False

            # check for default value
            try:
                lines = subprocess.check_output("grep -ir \""+var+"[[:space:]]*=[[:space:]]*\" "+i+" | grep -v \"=>\" | grep -v \"==\"", shell=True).splitlines()
            except:
                lines = []

            # check for type
            #lines = subprocess.check_output("grep -irE \"::([[:space:]|[:alnum:]|[:punct:]])*"+var+"\"", shell=True).splitlines()

            for line in lines:
                # check for assignment
                regex = r"\b{}\b[\s]*=[\s]*(?!=)".format(var)
                match1 = re.search(regex, line)

                # check for type
                regex = r"::[\s]*.*?\b{}\b".format(var)
                match2 = re.search(regex, line)

                if match1 and match2:
                    match_global = True
                    break

            #print match_global

            # query use statements
            if not match_global:
                try:
                    f2 = subprocess.check_output("grep -ir \""+var+"\" "+i+" | grep \"use[[:blank:]]\" | grep -vE \"^!\" | awk '{print $2}' | tr -d \",\" | uniq | sort", shell=True).splitlines()
                    if not f2:
                        try:
                            f2 = subprocess.check_output("grep -ir \"use[[:blank:]]\" "+i+" | grep -vE \"^!\" | awk '{print $2}' | tr -d \",\" | uniq | sort", shell=True).splitlines()
                        except:
                            pass

                    # find actual file that defines the use statement 
                    for j in f2:
                        k = subprocess.check_output("grep -ir \"module[[:blank:]]"+j+"\" fpp/* | awk -F: '{print $1}' | uniq", shell=True).splitlines()
                        if not k:
                            continue
                        file_str = file_str+k[0]+" "
                        #print file_str 
                except:
                    pass

        #print file_str     
        #sys.exit()
 
        # get list of lines that match with given variable name (specific files that has nml definition)
        #try:
        #    lines = subprocess.check_output("grep -irhw "+var+" "+file_str+" | grep -v \"^!\" | grep -v \"write(\"", shell=True).splitlines()
        #except:
        #    lines = subprocess.check_output("grep -irhwE "+var+" fpp/* | grep -v \"^!\" | grep -v \"write(\"", shell=True).splitlines()
        #lines = subprocess.check_output("grep -irhw "+var+" fpp/* | grep -v \"^!\" | grep -v \"write(\"", shell=True).splitlines()
        try:
            lines = subprocess.check_output("grep -irhw \""+var+"\" "+file_str+" | grep -v \"^!\" | grep -v \"write(\"", shell=True).splitlines()
        except:
            lines = []

        #print lines

        # remove unwanted lines
        lines = remove_values_from_list(lines, 'subroutine')
        lines = remove_values_from_list(lines, 'result')
        lines = remove_values_from_list(lines, 'call')
        lines = remove_values_from_list(lines, 'public')
        #lines = remove_values_from_list(lines, 'use')

        #print lines

        # find the type of variable
        for line in lines:
            line_fixed = line.strip('\n').lower().strip()

            regex = r"::[\s]*\b{}\b".format(var)
            match1 = re.search(regex, line_fixed)

            regex = r"::[\s]*.*?\b{}\b".format(var)
            match2 = re.search(regex, line_fixed)

            #print line_fixed, match1, match2

            match = False 
            if match1 or match2:
                var_type = line_fixed.split('::')[0].strip()
                var_type = var_type.split('(')[0].strip()
                var_type = var_type.replace('dimension', '').strip()
                var_type = var_type.replace('pointer', '').strip()
                var_type = var_type.replace('intent', '').strip()
                var_type = var_type.replace(',', '').strip()
                match = var_type in accepted_variable_types
            else:
                var_type = line_fixed.split(' ')[0].strip()
                match = var_type in accepted_variable_types

            if match:
                var_meta[nml+":"+var][0][0] = var_type
                break

        #  get list of lines that match with given variable name (all files)
        #lines = subprocess.check_output("grep -irhwE "+var+" fpp/* | grep -v \"^!\" | grep -v \"write(\"", shell=True).splitlines()

        # find the dimension of variable
        for line in lines:
            line_fixed = line.strip('\n').lower().strip()

            if 'intent' in line_fixed:
                continue 

            regex = r"\bdimension\(\b"
            match1 = re.search(regex, line_fixed)

            regex = r"::[\s]*\b{}\b".format(var)
            match2 = re.search(regex, line_fixed)

            regex = r"\b{}\b[\s]*\(".format(var)
            match3 = re.search(regex, line_fixed)

            #print line_fixed, match1, match2, match3

            indx = 0
            match = False 
            if match1 and match2:
                indx = match1.end()
                match = True
            if (match2 and match3) or match3:
                indx = match3.end()
                match = True

            #print line_fixed
 
            if match:
                var_dim = line_fixed[indx:].split(')')[0].strip()

                if var_meta[nml+":"+var][0][1] == 'None' or var_dim > var_meta[nml+":"+var][0][1]:
                    var_dim_splitted = var_dim.split(':')
                    var_dim_splitted = remove_values_from_list(var_dim_splitted, '')
                    var_dim_splitted = remove_values_from_list(var_dim_splitted, ':')

                    regex = r"^[0-9]+$"
                    var_dim_splitted_numeric = [re.search(regex,x) for x in var_dim_splitted]
                    var_dim_splitted_numeric = [x is None for x in var_dim_splitted_numeric]
                    #print var_dim, var_dim_splitted, var_dim_splitted_numeric

                    if all(var_dim_splitted_numeric):
                        var_meta[nml+":"+var][0][1] = var_dim
                    else:
                        var_meta[nml+":"+var][0][1] = var_dim_splitted[len(var_dim_splitted)-1]
                    break  

        # find the default value of variable
        for line in lines:
            line_fixed = line.strip('\n').lower().strip()
 
            # if there is a comment at the end of the line, just got until that point 
            # if variable not exist after trim, skip this line
            indx = line_fixed.find('!')
            if indx != -1:
                if indx < 1:
                    break
                line_fixed = line_fixed[:indx-1]
                if var not in line_fixed:
                    continue 
            
            # match for var =
            regex = r"\b{}\b[\s]*=[\s]*(?!=)".format(var)
            match1 = re.search(regex, line_fixed)

            # match for data var /
            regex = r"\b{}\b[\s]*/(?!=)".format(var)
            match2 = re.search(regex, line_fixed)

            # match for data var() = (/
            regex = r"\b{}\b[\s]*\([0-9]*\)[\s]*=[\s]*\(/".format(var)
            match3 = re.search(regex, line_fixed)

            # match for data var() = 
            regex = r"\b{}\b[\s]*\([0-9]*\)[\s]*=[\s]*".format(var)
            match4 = re.search(regex, line_fixed)

            # match for data dimension() var = (/ 
            regex = r"\b{}\b[\s]*=[\s]*\(/".format(var)
            match5 = re.search(regex, line_fixed)

            regex = r"\b{}\b[\s]*=[\s]*\b{}\b".format(var,var)
            match6 = re.search(regex, line_fixed)

            match = False
            isarray = False
            if match1 and not match6 and '%' not in line_fixed:
                var_default = line_fixed[match1.start():].split('=')[1].strip()
                match = True
            if match2 and not match6 and '%' not in line_fixed:
                var_default = line_fixed[match2.start():].split('/')[1].strip()
                match = True
            if match3 and not match6 and '%' not in line_fixed:
                var_default = line_fixed[match3.start():].split('(/')[1].replace('/)','').strip()
                isarray = True
                match = True
            if match4 and not match6 and '%' not in line_fixed:
                var_default = line_fixed[match4.start():].split('=')[1].strip()
                match = True
            if match5 and not match6 and '%' not in line_fixed:
                var_default = line_fixed[match5.start():].split('=')[1].replace('(/','').replace('/)','').strip()
                isarray = True
                match = True

            #print "* ", line_fixed, match, match1, match2, match3, match4, match5

            if match:
                # if defualt value is expression that can not be evaluated, skip
                rest = ''.join([x for x in var_default if not x.isdigit()]).replace('.', '')
                if rest in accepted_arit_opts:
                    continue

                # remove int functions
                for fn in int_func:
                    var_default = var_default.replace(fn, '')
                var_default = var_default.replace('(', '').replace(')', '')

                if not isarray:
                    var_default = var_default.split(',')[0].strip()
                var_default = var_default.split('!')[0].strip()
                var_default = var_default.replace('\'', '').strip()
                var_default = var_default.replace('/', '').strip()
                var_default = var_default.replace('&', '').strip()
                var_default = var_default.replace('"', '').strip()

                # eval operations, if it is required
                if ".e" in var_default.lower():
                    var_default = "{}".format(eval(var_default))
                    var_default = var_default.replace('(', '').replace(')', '')

                for opt in accepted_arit_opts:
                    if opt in var_default and not ('d'+opt in var_default.lower() or 'e'+opt in var_default.lower()):
                        try:
                            var_default = "{}".format(eval(var_default))
                            var_default = var_default.replace('(', '').replace(')', '')
                        except:
                            pass
                        break

                if len(var_default) > 0:
                   var_meta[nml+":"+var][0][2] = var_default

                   # if variable does not have data type, fill it from defualt value
                   if 'None' in var_meta[nml+":"+var][0][0]:
                       if 'None' in var_default or '.grb' in var_default:
                           var_meta[nml+":"+var][0][0] = 'character'
                       elif ".true." in var_default or ".false." in var_default:
                           var_meta[nml+":"+var][0][0] = 'logical'
                       elif "." in var_default:
                           var_meta[nml+":"+var][0][0] = 'real'
                       else:
                           var_meta[nml+":"+var][0][0] = 'integer'

                   break
                
        print nml, var, var_meta[nml+":"+var]

# write as xml file
with open("namelist.xml", 'w') as fout:
    # write xml definition
    fout.write("<?xml version=\"1.0\"?>\n")
    fout.write("<entry_id version=\"2.0\">\n\n")

    # add namelist sections
    for nml in nml_list:
        # add section description
        fout.write("<!-- =========================== -->\n")
        fout.write("<!-- "+nml+" -->\n")
        fout.write("<!-- =========================== -->\n\n")
               
        # add variables
        for var in var_dict[nml]:
            var_meta_lst = var_meta[nml+":"+var]
            fout.write("<entry id=\""+var+"\">\n")
            if ('None' in var_meta_lst[0][1]):
                fout.write("  <type>"+var_meta_lst[0][0]+"</type>\n")
            else:
                fout.write("  <type>"+var_meta_lst[0][0]+"("+var_meta_lst[0][1]+")</type>\n")
            fout.write("  <group>"+nml+"</group>\n")
            fout.write("  <desc></desc>\n")    
            fout.write("  <values>\n")
            fout.write("    <value>"+var_meta_lst[0][2]+"</value>\n")
            fout.write("  </values>\n")
            fout.write("</entry>\n\n")
    fout.write("</entry_id>\n")
