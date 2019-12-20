#!/bin/bash

# check command line arguments
if [ "$1" == "" ]; then
  echo "You need to specify namelist file! Exiting ..."
  exit
fi

nml=$1

# convert to unix format
dos2unix -q -n $nml input.txt
nml="input.txt"

# get list of variable
lst=`cat $nml | sort | grep -v "^[&|/]" | grep -v "_nml" | tr -d " " | sed '/^[[:space:]]*$/d'`

for i in $lst
do
  # get variable name
  vnm=`echo $i | awk -F= '{print $1}' | tr -d " " | tr '[:upper:]' '[:lower:]' | awk -F\( '{print $1}'`

  # get value in nml
  val_in_nml=`echo $i | awk -F= '{print $2}' | tr -d " " | tr '[:upper:]' '[:lower:]' | awk -F\( '{print $1}' | sed -e "s/^M//"`

  # special threatment for .t. and .f.
  val_in_nml=${val_in_nml/.t./.true.}
  val_in_nml=${val_in_nml/.T./.true.}
  val_in_nml=${val_in_nml/.f./.false.}
  val_in_nml=${val_in_nml/.F./.false.}
  
  # TODO: need to convert 10. to 10.0 but not .true.
  #if [[ $val_in_nml == *. ]] && [ "$val_in_nml" != "."] ; then 
  #  val_in_nml=`echo "${val_in_nml}0"`
  #fi

  # find section in xml file for given variable
  lno1=`cat -n namelist_definition_fv3.xml | grep -iw $vnm | head -n 1 | awk '{print $1}'`
  lno2=$lno1
  lno3=$lno1

  # check variable exist in xml file?
  if [ -z "$lno1" ]; then
    echo "*** no variable called >$vnm< in xml file!"
    continue
  fi
  continue
  # extract section from xml filr for given variable
  #echo "$vnm $lno1 $lno2 $lno3"
  while : 
  do
    # check that it is reached to the end of entry?
    str=`cat namelist_definition_fv3.xml | head -n $((lno2+1)) | tail -n 1`
  
    # exit if end of entry is reached?
    if [[ $str == *"</entry>"* ]]; then
      lno2=$((lno2+1))
      break
    fi

    # find line for last <value> tag
    if [[ $str == *"</value>"* ]]; then
      lno3=$((lno2+1))
    fi

    lno2=$((lno2+1))
  done
  #echo "$vnm $lno1 $lno2 $lno3"

  # get list of value/s
  SAVEIFS=$IFS
  IFS=$'\n'
  array=( $( cat namelist_definition_fv3.xml | head -n $lno2 | tail -n $((lno2-lno1+1)) ) )

  for v in "${array[@]}"
  do
    # check it is value or not?
    if [[ $v == *"</value>"* ]]; then
      # get value in xml, could be multiple entry
      val_in_xml=`echo $v | awk -F\> '{print $2}' | awk -F\< '{print $1}' | tr -d " "`

      # check value in nml same with value in xml?
      if [[ ${val_in_xml} == *"${val_in_nml}"* ]]; then
        str_add=""
        #break 
      else
        str_add="<value app=\"mrweather\">$val_in_nml</value>"
      fi

      #echo ${val_in_xml} ${val_in_nml} 
    fi  
  done

  # add new entry
  if [ -n "$str_add" ]; then  
    # add first part until last existing value entry
    array=( $( head -n $lno3 namelist_definition_fv3.xml | tail -n $((lno3-lno1+1)) ) )
    for line in "${array[@]}"
    do
      echo $line
    done

    # add new entry
    echo "    $str_add"

    # close entry
    array=( $( head -n $lno2 namelist_definition_fv3.xml | tail -n 2 ) )
    for line in "${array[@]}"
    do
      echo $line
    done
  #else
  #  # add as it is
  #  array=( $( head -n $lno2 namelist_definition_fv3.xml | tail -n $((lno2-lno1+1)) ) )
  #  for line in "${array[@]}"
  #  do
  #    echo $line
  #  done
  fi
  echo ""
done
