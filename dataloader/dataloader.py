import numpy as np
from sklearn.utils import shuffle
import torch
from .sampler import CategoriesSampler, SupportsetSampler, TrueIncreTrainCategoriesSampler

def custom_collate(batch):
    new_batch = []
    for b in batch:
        if isinstance(b, np.ndarray):
            # 针对 numpy 数组的数据类型进行转换
            if b.dtype == np.float32:
                new_batch.append(torch.tensor(b, dtype=torch.float32))
            elif b.dtype == np.int64:
                new_batch.append(torch.tensor(b, dtype=torch.long))
            else:
                new_batch.append(torch.tensor(b))  # 默认转换为 tensor
        elif isinstance(b, np.int64):
            # 处理 numpy.int64 类型的数据
            new_batch.append(torch.tensor(b, dtype=torch.long))
        elif isinstance(b, list):
            # 递归处理 list 中的元素
            new_batch.append([torch.tensor(item) for item in b])
        elif isinstance(b, tuple):
            # 递归处理 tuple 中的元素，保持 tuple 结构
            new_batch.append(tuple(custom_collate([item])[0] for item in b))
        elif isinstance(b, torch.Tensor):
            new_batch.append(b)  # 如果已经是 Tensor，直接添加
        else:
            raise TypeError(f"Unsupported data type: {type(b)}")  # 针对未处理类型抛出错误
    return torch.utils.data._utils.collate.default_collate(new_batch)




def get_dataloader(args, session):
    if session == 0:
        if args.project == 'base':
            trainset, valset, trainloader, valloader = get_pretrain_dataloader(args)
        elif args.project == 'stdu':
            trainset, valset, trainloader, valloader = get_base_dataloader_stdu(args)
        elif args.project == 'cec':
            trainset, valset, trainloader, valloader = get_base_dataloader_meta(args)
    else:
        trainset, valset, trainloader, valloader = get_new_dataloader(args, session)
    return trainset, valset, trainloader, valloader

def get_testloader(args, session):
    if args.tmp_train:
        num_base_class = args.stdu.num_tmpb
        num_incre_class = args.stdu.num_tmpi
    else:
        num_base_class = args.num_base
        num_incre_class = 0

    # test on all encountered classes
    class_new = get_session_classes(args, session)
    print(class_new)
    if args.dataset == 'FMC':
        testset = args.Dataset.FSDCLIPS(root=args.dataroot, phase="test",
                                      index=class_new, k=None)
    elif 'nsynth' in args.dataset:
        testset = args.Dataset.NDS(root=args.dataroot, phase="test",
                                      index=class_new, k=None, args=args)
    elif 'librispeech' in args.dataset:
        testset = args.Dataset.LBRS(root=args.dataroot, phase="test",
                                      index=class_new, k=None, args=args)
    elif args.dataset in ['f2n', 'f2l', 'n2f', 'n2l', 'l2f', 'l2n']:
        testset = args.Dataset.S2S(dataset=args.dataset, root=args.dataroot, phase="test",
                                index=class_new, k=None, args=args)
    testloader = torch.utils.data.DataLoader(dataset=testset, batch_size=args.dataloader.test_batch_size, shuffle=False,
                                             num_workers=args.dataloader.num_workers, pin_memory=True,collate_fn=custom_collate)

    return testset, testloader

def get_pretrain_dataloader(args):
    num_base = args.stdu.num_tmpb if args.tmp_train else args.num_base
    class_index = np.arange(num_base)

    if args.dataset == 'FMC':
        trainset = args.Dataset.FSDCLIPS(root=args.dataroot, phase="train",
                                             index=class_index, base_sess=True)
        valset = args.Dataset.FSDCLIPS(root=args.dataroot, phase="val", index=class_index, base_sess=True)
    elif 'nsynth' in args.dataset:
        trainset = args.Dataset.NDS(root=args.dataroot, phase="train",
                                             index=class_index, base_sess=True, args=args)
        valset = args.Dataset.NDS(root=args.dataroot, phase="val", index=class_index, base_sess=True, args=args)
    elif 'librispeech' in args.dataset:
        trainset = args.Dataset.LBRS(root=args.dataroot, phase="train",
                                             index=class_index, base_sess=True, args=args)
        valset = args.Dataset.LBRS(root=args.dataroot, phase="val", index=class_index, base_sess=True, args=args)
    elif args.dataset in ['f2n', 'f2l', 'n2f', 'n2l', 'l2f', 'l2n']:
        trainset = args.Dataset.S2S(dataset=args.dataset, root=args.dataroot, phase="train",
                                             index=class_index, base_sess=True, args=args)
        valset = args.Dataset.S2S(dataset=args.dataset, root=args.dataroot, phase="val", index=class_index, base_sess=True, args=args)
    trainloader = torch.utils.data.DataLoader(dataset=trainset, batch_size=args.dataloader.train_batch_size, shuffle=True,
                                              num_workers=8, pin_memory=True,collate_fn=custom_collate)
    valloader = torch.utils.data.DataLoader(
        dataset=valset, batch_size=args.dataloader.test_batch_size, shuffle=False, num_workers=8, pin_memory=True,collate_fn=custom_collate)

    return trainset, valset, trainloader, valloader

def get_base_dataloader_stdu(args):
    if args.tmp_train:
        num_base_class = args.stdu.num_tmpb
        num_incre_class = args.stdu.num_tmpi
    else:
        num_base_class = args.num_base
        num_incre_class = 0

    class_index = np.arange(num_base_class + num_incre_class)

    if args.dataset == 'FMC':
        trainset = args.Dataset.FSDCLIPS(root=args.dataroot, phase='train', index=class_index, k=None)
        valset = args.Dataset.FSDCLIPS(root=args.dataroot, phase='val', index=class_index, k=100) # k is same as new_loader's testset k
    # DataLoader(test_set, batch_sampler=sampler, num_workers=8, pin_memory=True)
    elif 'nsynth' in args.dataset:
        trainset = args.Dataset.NDS(root=args.dataroot, phase='train', index=class_index, k=None, args=args)
        valset = args.Dataset.NDS(root=args.dataroot, phase='val', index=class_index, k=None, args=args) # k is same as new_loader's testset k
    elif 'librispeech' in args.dataset:
        trainset = args.Dataset.LBRS(root=args.dataroot, phase='train', index=class_index, k=None, args=args)
        valset = args.Dataset.LBRS(root=args.dataroot, phase='val', index=class_index, k=None, args=args) # k is same as new_loader's testset k
    elif args.dataset in ['f2n', 'f2l', 'n2f', 'n2l', 'l2f', 'l2n']:
        trainset = args.Dataset.S2S(dataset=args.dataset, root=args.dataroot, phase='train', index=class_index, k=None, args=args)
        valset = args.Dataset.S2S(dataset=args.dataset, root=args.dataroot, phase='val', index=class_index, k=None, args=args) # k is same as new_loader's testset k
    # DataLoader(test_set, batch_sampler=sampler, num_workers=8, pin_memory=True)
    train_sampler = TrueIncreTrainCategoriesSampler(label=trainset.targets, n_batch=args.episode.train_episode, 
                                    na_base_cls=num_base_class, na_inc_cls=num_incre_class, 
                                    np_base_cls=args.episode.low_way, np_inc_cls=args.episode.episode_way,
                                    nb_shot=args.episode.low_shot,nn_shot=args.episode.episode_shot, n_query=args.episode.episode_query)
    trainloader = torch.utils.data.DataLoader(dataset=trainset, batch_sampler=train_sampler, num_workers=8,
                                                pin_memory=True,collate_fn=custom_collate)

    valloader = torch.utils.data.DataLoader(
        dataset=valset, batch_size=args.dataloader.test_batch_size, shuffle=False, num_workers=8, pin_memory=True,collate_fn=custom_collate)

    return trainset, valset, trainloader, valloader

def get_base_dataloader_stdu_cs(args):
    if args.tmp_train:
        num_base_class = args.stdu.num_tmpb
        num_incre_class = args.stdu.num_tmpi
    else:
        num_base_class = args.num_base
        num_incre_class = 0

    class_index = np.arange(num_base_class + num_incre_class)

    if args.dataset == 'FMC':
        trainset = args.Dataset.FSDCLIPS(root=args.dataroot, phase='train', index=class_index, k=None)
        valset = args.Dataset.FSDCLIPS(root=args.dataroot, phase='val', index=class_index, k=100) # k is same as new_loader's testset k
    # DataLoader(test_set, batch_sampler=sampler, num_workers=8, pin_memory=True)
    elif 'nsynth' in args.dataset:
        trainset = args.Dataset.NDS(root=args.dataroot, phase='train', index=class_index, k=None, args=args)
        valset = args.Dataset.NDS(root=args.dataroot, phase='val', index=class_index, k=None, args=args) # k is same as new_loader's testset k
    elif 'librispeech' in args.dataset:
        trainset = args.Dataset.LBRS(root=args.dataroot, phase='train', index=class_index, k=None, args=args)
        valset = args.Dataset.LBRS(root=args.dataroot, phase='val', index=class_index, k=None, args=args) # k is same as new_loader's testset k
    elif args.dataset in ['f2n', 'f2l', 'n2f', 'n2l', 'l2f', 'l2n']:
        trainset = args.Dataset.S2S(dataset=args.dataset, root=args.dataroot, phase='train', index=class_index, k=None, args=args)
        valset = args.Dataset.S2S(dataset=args.dataset, root=args.dataroot, phase='val', index=class_index, k=None, args=args) # k is same as new_loader's testset k
    # DataLoader(test_set, batch_sampler=sampler, num_workers=8, pin_memory=True)
    train_sampler = TrueIncreTrainCategoriesSampler(label=trainset.targets, n_batch=args.episode.train_episode, 
                                    na_base_cls=num_base_class, na_inc_cls=num_incre_class, 
                                    np_base_cls=num_base_class, np_inc_cls=args.episode.episode_way,
                                    nb_shot=args.episode.low_shot,nn_shot=args.episode.episode_shot, n_query=args.episode.episode_query)
    trainloader = torch.utils.data.DataLoader(dataset=trainset, batch_sampler=train_sampler, num_workers=8,
                                                pin_memory=True,collate_fn=custom_collate)

    valloader = torch.utils.data.DataLoader(
        dataset=valset, batch_size=args.dataloader.test_batch_size, shuffle=False, num_workers=8, pin_memory=True,collate_fn=custom_collate)

    return trainset, valset, trainloader, valloader



def get_dataset_for_data_init(args):
    if args.tmp_train:
        num_base_class = args.stdu.num_tmpb
        num_incre_class = args.stdu.num_tmpi
    else:
        num_base_class = args.num_base
        num_incre_class = 0

    class_index = np.arange(num_base_class)

    if args.dataset == 'FMC':
        trainset = args.Dataset.FSDCLIPS(root=args.dataroot, phase='train', index=class_index, k=None)
    elif 'nsynth' in args.dataset:
        trainset = args.Dataset.NDS(root=args.dataroot, phase='train', index=class_index, k=None, args=args)
    elif 'librispeech' in args.dataset:
        trainset = args.Dataset.LBRS(root=args.dataroot, phase='train', index=class_index, k=None, args=args)
    elif args.dataset in ['f2n', 'f2l', 'n2f', 'n2l', 'l2f', 'l2n']:   
        trainset = args.Dataset.S2S(dataset=args.dataset, root=args.dataroot, phase='train', index=class_index, k=None, args=args)
    return trainset

def get_new_dataloader(args, session):
    if args.tmp_train:
        num_base_class = args.stdu.num_tmpb
        num_incre_class = args.stdu.num_tmpi
    else:
        num_base_class = args.num_base
        num_incre_class = 0

    assert session > 0
    if args.dataset == 'FMC':
        #session_classes = np.arange(num_base_class + (session -1) * args.way, num_base_class + session * args.way)
        #trainset = args.Dataset.FSDCLIPS(root=args.dataroot, phase='train', index=session_classes, k=None)
        if session % 2 == 1:
            session_classes = np.arange(num_base_class + (session //2) * args.way, num_base_class + (session//2 + 1) * args.way)
            trainset = args.Dataset.FSDCLIPS(root=args.dataroot, phase='train', index=session_classes, k=None, args=args)
        else:  
            session_classes = np.arange(num_base_class + (session /2 - 1) * args.way, num_base_class + (session/2 ) * args.way)
            trainset = args.Dataset.FSDCLIPS(root=args.dataroot, phase='train', index=session_classes, k=None, args=args)
    elif 'nsynth' in args.dataset:
        #session_classes = np.arange(num_base_class + (session -1) * args.way, num_base_class + session * args.way)
        #trainset = args.Dataset.NDS(root=args.dataroot, phase='train', index=session_classes, k=None, args=args)
        if session % 2 == 1:
            session_classes = np.arange(num_base_class + (session //2) * args.way, num_base_class + (session//2 + 1) * args.way)
            trainset = args.Dataset.NDS(root=args.dataroot, phase='train', index=session_classes, k=None, args=args)
        else:  
            session_classes = np.arange(num_base_class + (session /2 - 1) * args.way, num_base_class + (session/2 ) * args.way)
            trainset = args.Dataset.NDS(root=args.dataroot, phase='train', index=session_classes, k=None, args=args)
    elif 'librispeech' in args.dataset:
        #if session <= 8:
        #     session_classes = np.arange(num_base_class + (session -1) * args.way, num_base_class + session * args.way)
        ##else:  
        #     session_classes = np.arange(num_base_class + (16-session) * args.way, num_base_class + (16-session) * args.way)
        #     trainset = args.Dataset.LBRS(root=args.dataroot, phase='train', index=session_classes, k=None, args=args) 
        if session % 2 == 1:
            session_classes = np.arange(num_base_class + (session //2) * args.way, num_base_class + (session//2 + 1) * args.way)
            trainset = args.Dataset.LBRS(root=args.dataroot, phase='train', index=session_classes, k=None, args=args)
        else:  
            session_classes = np.arange(num_base_class + (session /2 - 1) * args.way, num_base_class + (session/2 ) * args.way)
            trainset = args.Dataset.LBRS(root=args.dataroot, phase='train', index=session_classes, k=None, args=args) 

    elif args.dataset in ['f2n', 'f2l', 'n2f', 'n2l', 'l2f', 'l2n']:
        session_classes = np.arange(num_base_class + (session -1) * args.way, num_base_class + session * args.way)
        trainset = args.Dataset.S2S(dataset=args.dataset, root=args.dataroot, phase='train', index=session_classes, k=None, args=args)
    train_sampler = SupportsetSampler(label=trainset.targets, n_cls=args.episode.episode_way, 
                                n_per=args.episode.episode_shot,n_batch=1, seq_sample=args.seq_sample)

    trainloader = torch.utils.data.DataLoader(dataset=trainset, batch_sampler=train_sampler, num_workers=8,
                                                pin_memory=True,collate_fn=custom_collate)
                                                
    class_new = get_session_classes(args, session)

    if args.dataset == 'FMC':
        valset = args.Dataset.FSDCLIPS(root=args.dataroot, phase='val', index=class_new, k=None)
    if 'nsynth' in args.dataset:
        valset = args.Dataset.NDS(root=args.dataroot, phase='val', index=class_new, k=None, args=args)
    if 'librispeech' in args.dataset:
        valset = args.Dataset.LBRS(root=args.dataroot, phase='val', index=class_new, k=None, args=args)
    elif args.dataset in ['f2n', 'f2l', 'n2f', 'n2l', 'l2f', 'l2n']:
        valset = args.Dataset.S2S(dataset=args.dataset, root=args.dataroot, phase='val', index=class_new, k=None, args=args)
    valloader = torch.utils.data.DataLoader(dataset=valset, batch_size=args.dataloader.test_batch_size, shuffle=False,
                                                num_workers=8, pin_memory=True,collate_fn=custom_collate)
    return trainset, valset, trainloader, valloader

def get_session_classes_8(args,  session):
    if args.tmp_train:
        num_base_class = args.stdu.num_tmpb
        num_incre_class = args.stdu.num_tmpi
    else:
        num_base_class = args.num_base
        num_incre_class = 0

    if session <= 8:                  #5\6\7\8session类递减
        class_list = np.arange(num_base_class + session * args.way)
    else:
        class_list = np.arange(num_base_class + (16-session) * args.way)


    #class_list = np.arange(num_base_class + session * args.way)
    return class_list

def get_session_classes(args,  session):
    m=1
    if args.tmp_train:
        num_base_class = args.stdu.num_tmpb
        num_incre_class = args.stdu.num_tmpi
    else:
        num_base_class = args.num_base
        num_incre_class = 0
    g=args.g
    if session % 2 == 1:  # session 为奇数时
           cd=session//2
           if cd == 0:
                m=0
           elif cd == 1:
                c=np.arange(60-g,64-g)#64
           elif cd == 2:
                c=np.concatenate((np.arange(60-g,64-g),np.arange(65-g,69-g)))     
           elif cd == 3:
                c=np.concatenate((np.arange(60-g,64-g),np.arange(65-g,69-g),np.arange(70-g,74-g)))
           elif cd == 4:
                c=np.concatenate((np.arange(60-g,64-g),np.arange(65-g,69-g),np.arange(70-g,74-g),np.arange(75-g,79-g)))
           elif cd == 5:
                c=np.concatenate((np.arange(60-g,64-g),np.arange(65-g,69-g),np.arange(70-g,74-g),np.arange(75-g,79-g),np.arange(80-g,84-g)))
           elif cd == 6:
                c=np.concatenate((np.arange(60-g,64-g),np.arange(65-g,69-g),np.arange(70-g,74-g),np.arange(75-g,79-g),np.arange(80-g,84-g),np.arange(85-g,89-g)))
           else:
               c=np.concatenate((np.arange(60-g,64-g),np.arange(65-g,69-g),np.arange(70-g,74-g),np.arange(75-g,79-g),np.arange(80-g,84-g),np.arange(85-g,89-g),np.arange(90-g,94-g)))
           if m==0:
               class_list = np.concatenate((np.arange(num_base_class), #-cd
                                 np.arange(num_base_class + (session //2 ) * args.way, 
                                           num_base_class + (session // 2 + 1) * args.way)))
           else:
               class_list = np.concatenate((np.arange(num_base_class-(cd)), c,      #-cd
                                 np.arange(num_base_class + (session //2 ) * args.way, 
                                           num_base_class + (session // 2 + 1) * args.way)))
    else:  # session 为偶数时
           ci=session//2
           if session==0:
                m=0
           elif session == 2:
                c=np.arange(60-g,64-g)
           elif session == 4:
                c=np.concatenate((np.arange(60-g,64-g),np.arange(65-g,69-g)))     
           elif session == 6:
                c=np.concatenate((np.arange(60-g,64-g),np.arange(65-g,69-g),np.arange(70-g,74-g)))
           elif session == 8:
                c=np.concatenate((np.arange(60-g,64-g),np.arange(65-g,69-g),np.arange(70-g,74-g),np.arange(75-g,79-g)))
           elif session == 10:
                c=np.concatenate((np.arange(60-g,64-g),np.arange(65-g,69-g),np.arange(70-g,74-g),np.arange(75-g,79-g),np.arange(80-g,84-g)))
           elif session == 12:
                c=np.concatenate((np.arange(60-g,64-g),np.arange(65-g,69-g),np.arange(70-g,74-g),np.arange(75-g,79-g),np.arange(80-g,84-g),np.arange(85-g,89-g)))
           elif session == 14:
                c=np.concatenate((np.arange(60-g,64-g),np.arange(65-g,69-g),np.arange(70-g,74-g),np.arange(75-g,79-g),np.arange(80-g,84-g),np.arange(85-g,89-g),np.arange(90-g,94-g)))
           else:
                c=np.concatenate((np.arange(60-g,64-g),np.arange(65-g,69-g),np.arange(70-g,74-g),np.arange(75-g,79-g),np.arange(80-g,84-g),np.arange(85-g,89-g),np.arange(90-g,94-g),np.arange(95-g,99-g)))
           if m==0:
               class_list = np.arange(num_base_class)
           else:
               class_list = np.concatenate((np.arange(num_base_class-(ci)), c))#-ci
    return class_list


def get_incre_dataloader(args, session):
    if args.tmp_train:
        num_base_class = args.stdu.num_tmpb
        num_incre_class = args.stdu.num_tmpi
    else:
        num_base_class = args.num_base
        num_incre_class = 0

    assert session > 0
    if args.dataset == 'FMC':
        session_classes = np.arange(num_base_class + (session -1) * args.way, num_base_class + session * args.way)
        trainset = args.Dataset.FSDCLIPS(root=args.dataroot, phase='train', index=session_classes, k=None)
    elif 'nsynth' in args.dataset:
        session_classes = np.arange(num_base_class + (session -1) * args.way, num_base_class + session * args.way)
        trainset = args.Dataset.NDS(root=args.dataroot, phase='train', index=session_classes, k=None, args=args)
    elif 'librispeech' in args.dataset:
            session_classes = np.arange(num_base_class + (session -1) * args.way, num_base_class + session * args.way)
            trainset = args.Dataset.LBRS(root=args.dataroot, phase='train', index=session_classes, k=None, args=args)
    elif args.dataset in ['f2n', 'f2l', 'n2f', 'n2l', 'l2f', 'l2n']:
        session_classes = np.arange(num_base_class + (session -1) * args.way, num_base_class + session * args.way)
        trainset = args.Dataset.S2S(dataset=args.dataset, root=args.dataroot, phase='train', index=session_classes, k=None, args=args)
    train_sampler = SupportsetSampler(label=trainset.targets, n_cls=args.episode.episode_way, 
                                n_per=args.episode.episode_shot,n_batch=1, seq_sample=args.seq_sample)

    trainloader = torch.utils.data.DataLoader(dataset=trainset, batch_sampler=train_sampler, num_workers=8,
                                                pin_memory=True,collate_fn=custom_collate)
                                                
    class_new = get_val_session_classes(args, session)
    if args.dataset == 'FMC':
        valset = args.Dataset.FSDCLIPS(root=args.dataroot, phase='val', index=class_new, k=None)
    if 'nsynth' in args.dataset:
        valset = args.Dataset.NDS(root=args.dataroot, phase='val', index=class_new, k=None, args=args)
    if 'librispeech' in args.dataset:
        valset = args.Dataset.LBRS(root=args.dataroot, phase='val', index=class_new, k=None, args=args)
    elif args.dataset in ['f2n', 'f2l', 'n2f', 'n2l', 'l2f', 'l2n']:
        valset = args.Dataset.S2S(dataset=args.dataset, root=args.dataroot, phase='val', index=class_new, k=None, args=args)
    valloader = torch.utils.data.DataLoader(dataset=valset, batch_size=args.dataloader.test_batch_size, shuffle=False,
                                                num_workers=8, pin_memory=True,collate_fn=custom_collate)
    return trainset, valset, trainloader, valloader

def get_val_session_classes(args,  session):
    if args.tmp_train:
        num_base_class = args.stdu.num_tmpb
        num_incre_class = args.stdu.num_tmpi
    else:
        num_base_class = args.num_base
        num_incre_class = 0
    class_list = np.arange(num_base_class + session * args.way)
    return class_list




def get_base_dataloader_meta(args):
    class_index = np.arange(args.num_base)

    if args.dataset == 'FMC':
        trainset = args.Dataset.FSDCLIPS(root=args.dataroot, phase='train', index=class_index, k=None)
        valset = args.Dataset.FSDCLIPS(root=args.dataroot, phase='val', index=class_index, k=None) # k is same as new_loader's testset k
    elif 'nsynth' in args.dataset:
        trainset = args.Dataset.NDS(root=args.dataroot, phase='train', index=class_index, k=None, args=args)
        valset = args.Dataset.NDS(root=args.dataroot, phase='val', index=class_index, k=100, args=args) # k is same as new_loader's testset k
    elif 'librispeech' in args.dataset:
        trainset = args.Dataset.LBRS(root=args.dataroot, phase='train', index=class_index, k=None, args=args)
        valset = args.Dataset.LBRS(root=args.dataroot, phase='val', index=class_index, k=100, args=args) # k is same as new_loader's testset k
    elif args.dataset in ['f2n', 'f2l', 'n2f', 'n2l', 'l2f', 'l2n']:
        trainset = args.Dataset.S2S(dataset=args.dataset, root=args.dataroot, phase='train', index=class_index, k=None, args=args)
        valset = args.Dataset.S2S(dataset=args.dataset, root=args.dataroot, phase='val', index=class_index, k=100, args=args) # k is same as new_loader's testset k 
    # DataLoader(test_set, batch_sampler=sampler, num_workers=8, pin_memory=True)
    elif 'fsd' in args.dataset:
        trainset = args.Dataset.FSD(root=args.dataroot, phase='train', index=class_index, k=None, args=args)
        valset = args.Dataset.FSD(root=args.dataroot, phase='val', index=class_index, k=100, args=args) # k is same as new_loader's testset k
    sampler = CategoriesSampler(label=trainset.targets, n_batch=args.episode2.train_episode, n_cls=args.episode2.episode_way,
                                n_per=(args.episode2.episode_shot + args.episode2.episode_query))

    trainloader = torch.utils.data.DataLoader(dataset=trainset, batch_sampler=sampler, num_workers=8,
                                                pin_memory=True,collate_fn=custom_collate)

    valloader = torch.utils.data.DataLoader(
        dataset=valset, batch_size=args.dataloader.test_batch_size, shuffle=False, num_workers=8, pin_memory=True,collate_fn=custom_collate)

    return trainset, valset, trainloader, valloader