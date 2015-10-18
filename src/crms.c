/*
 * Conditional reverse complement Rescale Mark Split
 * For inline Loeb adapters only.
 */

#include "crms.h"

/*
 * Random not needed work.
 * 1. Creating the special family size one case.
 * 2. digitslut (sprintf)
 */


void print_crms_usage(char *argv[])
{
		fprintf(stderr, "Usage: %s <options> <Fq.R1.seq> <Fq.R2.seq>"
						"\nFlags:\n"
						"-l: Number of nucleotides at the beginning of each read to "
						"use for barcode. Final barcode length is twice this. REQUIRED.\n"
						"-s: homing sequence. REQUIRED.\n"
						"-o: Output basename. Defaults to a variation on input filename.\n"
						"-t: Homopolymer failure threshold. A molecular barcode with"
						" a homopolymer of length >= this limit is flagged as QC fail."
						"Default: 10.\n"
						"-n: Number of nucleotides at the beginning of the barcode to use to split the output. Default: 4.\n"
						"-m: Mask first n nucleotides in read for barcode. Default: 0. Recommended: 1.\n"
						"-p: Number of threads to use if running uthash_dmp.\n"
						"-d: Use this flag to to run hash_dmp.\n"
						"-f: If running hash_dmp, this sets the Final Fastq Prefix. \n"
						"The Final Fastq files will be named '<ffq_prefix>.R1.fq' and '<ffq_prefix>.R2.fq'.\n"
						"-r: Path to flat text file with rescaled quality scores. If not provided, it will not be used.\n"
						"-v: Maximum barcode length for a variable length barcode dataset. If left as default value,"
						" (-1), other barcode lengths will not be considered.\n"
						"-z: Flag to optionally pipe to gzip while producing final fastqs. Default: False.\n"
						"-g: Gzip compression ratio if piping to gzip (-z). Default: 6 (default).\n"
						"-c: Flag to optionally cat all files together in one command. Faster than sequential cats, but might break."
						"In addition, won't work for enormous filenames or too many arguments. Default: False.\n"
						"-u: Set notification/update interval for split. Default: 1000000.\n"
						"-h: Print usage.\n", argv[0]);
}

void print_crms_opt_err(char *argv[], char *optarg)
{
	print_crms_usage(argv);
	fprintf(stderr, "Unrecognized option %s. Abort!\n", optarg);
	exit(1);
}



/*
 * Pre-processes (pp) and splits fastqs with inline barcodes.
 */
mark_splitter_t *pp_split_inline(mssi_settings_t *settings)
{
	fprintf(stderr, "Now beginning pp_split_inline with fastq paths %s and %s.\n", settings->input_r1_path, settings->input_r2_path);
	if(!(strcmp(settings->input_r1_path, settings->input_r2_path))) {
		fprintf(stderr, "Hey, it looks like you're trying to use the same path for both r1 and r2. At least try to fool me by making a symbolic link.\n");
		exit(EXIT_FAILURE);
	}
	if(settings->rescaler_path) {
		settings->rescaler = parse_1d_rescaler(settings->rescaler_path);
	}
	mark_splitter_t *splitter = (mark_splitter_t *)malloc(sizeof(mark_splitter_t));
	*splitter = init_splitter_inline(settings);
	gzFile fp1 = gzopen(settings->input_r1_path, "r");
	gzFile fp2 = gzopen(settings->input_r2_path, "r");
	kseq_t *seq1 = kseq_init(fp1);
	kseq_t *seq2 = kseq_init(fp2);
	mseq_t *rseq1, *rseq2;
	int l1, l2;
	uint64_t bin;
	int count = 0;
	char pass_fail;
	settings->blen1_2 = settings->blen / 2;
	char *barcode = (char *)malloc((settings->blen + 1) * sizeof(char));
	barcode[settings->blen] = '\0'; // Null-terminate
	l1 = kseq_read(seq1);
	l2 = kseq_read(seq2);
	fprintf(stderr, "Read length for dataset: %i.\n", seq1->seq.l);
#if !NDEBUG
	int arr_size = seq1->seq.l * 4 * 2 * 39;
	if(settings->rescaler) {
		for(int i = 0; i < arr_size; ++i) {
			if(settings->rescaler[i] < 0) {
				fprintf(stderr, "Rescaler's got a negative number in pp_split_inline. WTF? %i. Index: %i.\n", settings->rescaler[i], i);
				exit(EXIT_FAILURE);
			}
			else if(settings->rescaler[i] == 0) {
				fprintf(stderr, "Rescaler's got a zero in pp_split_inline. WTF? %i. Index: %i.\n", settings->rescaler[i], i);
				exit(EXIT_FAILURE);
			}
		}
	}
#endif
	if(l1 < 0 || l2 < 0) {
			fprintf(stderr, "Could not open fastqs for reading. Abort!\n");
			FREE_MSSI_SETTINGS_PTR(settings);
			FREE_SPLITTER_PTR(splitter);
			exit(EXIT_FAILURE);
	}
	tmp_mseq_t *tmp = init_tm_ptr(seq1->seq.l, settings->blen);
	int n_len = nlen_homing_seq(seq1, seq2, settings);
	// Get first barcode.
	set_barcode(seq1, seq2, barcode, settings->offset, settings->blen1_2);
	pass_fail = (n_len > 0) ? test_hp_inline(barcode, settings->blen, settings->hp_threshold) : '0';
	//fprintf(stderr, "Initializing rseq1.\n");
	rseq1 = init_crms_mseq(seq1, barcode, settings->rescaler, tmp, (n_len > 0) ? n_len: settings->max_blen + settings->offset + settings->homing_sequence_length, 0);
	//fprintf(stderr, "Initializing rseq2.\n");
	rseq2 = init_crms_mseq(seq2, barcode, settings->rescaler, tmp, (n_len > 0) ? n_len: settings->max_blen + settings->offset + settings->homing_sequence_length, 1);
	bin = get_binnerul(barcode, settings->n_nucs);
	mseq2fq_inline(splitter->tmp_out_handles_r1[bin], rseq1, pass_fail);
	mseq2fq_inline(splitter->tmp_out_handles_r2[bin], rseq2, pass_fail);
	do {
		if(++count % settings->notification_interval == 0) {
			fprintf(stderr, "Number of records processed: %i.\n", count);
		}
		// Iterate through second fastq file.
		n_len = nlen_homing_seq(seq1, seq2, settings);
		set_barcode(seq1, seq2, barcode, settings->offset, settings->blen1_2);
		pass_fail = (n_len > 0) ? test_hp_inline(barcode, settings->blen, settings->hp_threshold) : '0';
		//fprintf(stdout, "Randomly testing to see if the reading is working. %s", seq1->seq.s);
		update_mseq(rseq1, barcode, seq1, settings->rescaler, tmp, (n_len > 0) ? n_len: settings->max_blen + settings->offset + settings->homing_sequence_length, 0);
		update_mseq(rseq2, barcode, seq2, settings->rescaler, tmp, (n_len > 0) ? n_len: settings->max_blen + settings->offset + settings->homing_sequence_length, 1);
		bin = get_binnerul(barcode, settings->n_nucs);
		mseq2fq_inline(splitter->tmp_out_handles_r1[bin], rseq1, pass_fail);
		mseq2fq_inline(splitter->tmp_out_handles_r2[bin], rseq2, pass_fail);
	} while (((l1 = kseq_read(seq1)) >= 0) && ((l2 = kseq_read(seq2)) >= 0));
	for(int i = 0; i < splitter->n_handles; ++i) {
		fclose(splitter->tmp_out_handles_r1[i]);
		fclose(splitter->tmp_out_handles_r2[i]);
	}
	tm_destroy(tmp);
	mseq_destroy(rseq1);
	mseq_destroy(rseq2);
	free(barcode);
	kseq_destroy(seq1);
	kseq_destroy(seq2);
	gzclose(fp1);
	gzclose(fp2);
	fprintf(stderr, "Successfully completed pp_split_inline.\n");
	return splitter;
}


int main(int argc, char *argv[])
{
	// Build settings struct
	int hp_threshold;
	int n_nucs;
	char *output_basename;
	const char *default_basename = "metasyntactic_var";
	mssi_settings_t settings = {
		.hp_threshold = 10,
		.n_nucs = 4,
		.output_basename = NULL,
		.input_r1_path = NULL,
		.input_r2_path = NULL,
		.homing_sequence = NULL,
		.n_handles = 0,
		.notification_interval = 1000000,
		.blen = 0,
		.homing_sequence_length = 0,
		.offset = 0,
		.rescaler = NULL,
		.rescaler_path = NULL,
		.run_hash_dmp = 0,
		.ffq_prefix = NULL,
		.threads = 1,
		.max_blen = -1,
		.gzip_output = 0,
		.panthera = 0,
		.gzip_compression = 6
	};
	omp_set_dynamic(0); // Tell omp that I want to set my number of threads 4realz
	int c;
	while ((c = getopt(argc, argv, "t:o:n:s:l:m:r:p:f:v:u:g:i:zcdh")) > -1) {
		switch(c) {
			case 'c': settings.panthera = 1; break;
			case 'd': settings.run_hash_dmp = 1; break;
			case 'f': settings.ffq_prefix = strdup(optarg); break;
			case 'g': settings.gzip_compression = atoi(optarg); break;
			case 'h': print_crms_usage(argv); return 0;
			case 'l': settings.blen = 2 * atoi(optarg); break;
			case 'm': settings.offset = atoi(optarg); break;
			case 'n': settings.n_nucs = atoi(optarg); break;
			case 'o': settings.output_basename = strdup(optarg); break;
			case 'p': settings.threads = atoi(optarg); omp_set_num_threads(settings.threads); break;
			case 'r': settings.rescaler_path = strdup(optarg); break;
			case 's': settings.homing_sequence = strdup(optarg); settings.homing_sequence_length = strlen(settings.homing_sequence); break;
			case 't': settings.hp_threshold = atoi(optarg); break;
			case 'u': settings.notification_interval = atoi(optarg); break;
			case 'v': settings.max_blen = atoi(optarg); break;
			case 'z': settings.gzip_output = 1; break;
			default: print_crms_opt_err(argv, optarg);
		}
	}

	if(argc < 5) {
		print_crms_usage(argv); exit(1);
	}

	settings.n_handles = ipow(4, settings.n_nucs);
	if(settings.n_handles * 3 > get_fileno_limit()) {
		int o_fnl = get_fileno_limit();
		increase_nofile_limit(kroundup32(settings.n_handles));
		fprintf(stderr, "Increased nofile limit from %i to %i.\n", o_fnl,
				kroundup32(settings.n_handles));
	}
	if(settings.ffq_prefix && !settings.run_hash_dmp) {
		fprintf(stderr, "Final fastq prefix option provided but run_hash_dmp not selected."
				"Either eliminate the -f flag or add the -d flag.\n");
		exit(EXIT_FAILURE);
	}

	if(!settings.homing_sequence) {
		fprintf(stderr, "Homing sequence not provided. Required.\n");
		exit(EXIT_FAILURE);
	}
	if(!settings.blen) {
		fprintf(stderr, "Barcode length not provided. Required. Abort!\n");
		exit(EXIT_FAILURE);
	}

	if(settings.max_blen > 0 && settings.max_blen * 2 < settings.blen) {
		fprintf(stderr, "max blen (%i) must be less than the minimum blen provided (%i).\n", settings.max_blen,
				settings.blen / 2);
	}

	if(settings.offset) {
		settings.blen -= 2 * settings.offset;
	}

	fprintf(stderr, "About to get the read paths.\n");
	if(argc - 1 != optind + 1) {
		fprintf(stderr, "Both read 1 and read 2 fastqs are required. See usage.\n", argc, optind);
		print_crms_usage(argv);
		return 1;
	}
	settings.input_r1_path = strdup(argv[optind]);
	settings.input_r2_path = strdup(argv[optind + 1]);

	if(!settings.output_basename) {
		settings.output_basename = make_crms_outfname(settings.input_r1_path);
		fprintf(stderr, "Output basename not provided. Defaulting to variation on input: %s.\n", settings.output_basename);
	}
	mark_splitter_t *splitter = pp_split_inline(&settings);
	cond_free(settings.rescaler);
	if(settings.run_hash_dmp) {
		fprintf(stderr, "Now executing hash dmp.\n");
		if(!settings.ffq_prefix) {
			settings.ffq_prefix = make_default_outfname(settings.input_r1_path, ".dmp.final");
		}
		// Whatever I end up putting into here.
		splitterhash_params_t *params = init_splitterhash(&settings, splitter);
		char del_buf[500];
#if NOPARALLEL
#else
		#pragma omp parallel
		{
#if !NDEBUG
			fprintf(stderr, "Now running dmp block in parallel with %i threads.\n", omp_get_num_threads());
#endif
			#pragma omp for
#endif
			for(int i = 0; i < settings.n_handles; ++i) {
				char tmpbuf[500];
				fprintf(stderr, "Now running omgz core on input filename %s and output filename %s.\n",
						params->infnames_r1[i], params->outfnames_r1[i]);
				omgz_core(params->infnames_r1[i], params->outfnames_r1[i]);

				omgz_core(params->infnames_r2[i], params->outfnames_r2[i]);
				fprintf(stderr, "Now removing temporary files %s and %s.\n",
						params->infnames_r1[i], params->infnames_r2[i]);
				sprintf(tmpbuf, "rm %s %s", params->infnames_r1[i], params->infnames_r2[i]);
				system(tmpbuf);
			}
#if NOPARALLEL
#else
		}
#endif
		// Remove temporary split files
		int sys_call_ret;
		char cat_buff[CAT_BUFFER_SIZE];
		char ffq_r1[200];
		char ffq_r2[200];
		sprintf(ffq_r1, "%s.R1.fq", settings.ffq_prefix);
		sprintf(ffq_r2, "%s.R2.fq", settings.ffq_prefix);
		sprintf(cat_buff, settings.gzip_output ? "> %s.gz" : "> %s", ffq_r1);
		sys_call_ret = system(cat_buff);
		sprintf(cat_buff, settings.gzip_output ? "> %s.gz" : "> %s", ffq_r2);
		sys_call_ret = system(cat_buff);
		char cat_buff1[CAT_BUFFER_SIZE] = "/bin/cat ";
		if(settings.panthera) {
			fprintf(stderr, "Now building cat string.\n");
			char cat_buff2[CAT_BUFFER_SIZE] = "/bin/cat ";
			for(int i = 0; i < settings.n_handles; ++i) {
				strcat(cat_buff1, params->outfnames_r1[i]);
				strcat(cat_buff1, " ");
				strcat(cat_buff2, params->outfnames_r2[i]);
				strcat(cat_buff2, " ");
			}
			if(settings.gzip_output) {
				sprintf(del_buf, " | gzip - -%i ", settings.gzip_compression);
				strcat(cat_buff1, del_buf);
				strcat(cat_buff2, del_buf);
			}
			strcat(cat_buff1, " > ");
			strcat(cat_buff1, ffq_r1);
			strcat(cat_buff2, " > ");
			strcat(cat_buff2, ffq_r2);
			if(settings.gzip_output) {
				strcat(cat_buff1, ".gz");
				strcat(cat_buff2, ".gz");
			}
			fprintf(stderr, "Now calling cat string '%s'.\n", cat_buff1);
			CHECK_CALL(cat_buff1, sys_call_ret);
			fprintf(stderr, "Now calling cat string '%s'.\n", cat_buff2);
			CHECK_CALL(cat_buff2, sys_call_ret);
		}
		else {
			for(int i = 0; i < settings.n_handles; ++i) {
				// Clear files if present
				sprintf(cat_buff, (settings.gzip_output) ? "cat %s | gzip - -3 >> %s": "cat %s >> %s", params->outfnames_r1[i], ffq_r1);
				sys_call_ret = system(cat_buff);
				if(sys_call_ret < 0) {
					fprintf(stderr, "System call failed. Command : '%s'.\n", cat_buff);
					exit(EXIT_FAILURE);
				}
				sprintf(cat_buff, (settings.gzip_output) ? "cat %s | gzip - -3 >> %s": "cat %s >> %s", params->outfnames_r2[i], ffq_r2);
				sys_call_ret = system(cat_buff);
				if(sys_call_ret < 0) {
					fprintf(stderr, "System call failed. Command : '%s'.\n", cat_buff);
					exit(EXIT_FAILURE);
				}
			}
		}
		#pragma omp parallel for shared(params)
		for(int i = 0; i < params->n; ++i) {
			char tmpbuf[500];
			sprintf(tmpbuf, "rm %s %s", params->outfnames_r1[i], params->outfnames_r2[i]);
			fprintf(stderr, "About to call command '%s'.\n", tmpbuf);
			CHECK_CALL(tmpbuf, sys_call_ret);
		}
		splitterhash_destroy(params);
		free(settings.ffq_prefix);
	}
	free_mssi_settings(settings);
	FREE_SPLITTER_PTR(splitter);
	return 0;
}